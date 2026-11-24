//+------------------------------------------------------------------+
//| GOLD_M1_MICRO_SCALPER.mq5                                        |
//| Tick-driven XAUUSD M1 momentum scalper                            |
//| Requires a HEDGING account for independent position management.  |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Gold M1 micro-scalper with noise filters, stepped entries and per-ticket trailing locks."

#include <Trade/Trade.mqh>
CTrade trade;

input group "GENERAL"
input ulong  InpMagic                 = 26112301;
input double InpLots                  = 0.01;
input int    InpMaxTrades              = 10;
input bool   InpAllowBuy               = true;
input bool   InpAllowSell              = true;
input int    InpDeviationPoints        = 20;

input group "ENTRY / NOISE FILTER"
input int    InpFastEMA                = 5;
input int    InpSlowEMA                = 13;
input int    InpADXPeriod              = 14;
input double InpMinADX                 = 18.0;
input int    InpATRPeriod              = 14;
input double InpMinATRPrice            = 0.03;
input double InpMaxATRPrice            = 3.00;
input int    InpMaxSpreadPoints        = 60;
input double InpEntryStepPrice         = 0.20; // Gold price units; e.g. 0.20 means $0.20 move on XAUUSD

input group "PROTECTION / TRAILING"
input double InpInitialStopPrice      = 0.60;
input double InpTrailStartPrice       = 0.30;
input double InpTrailDistancePrice    = 0.15;
input double InpDailyLossLimitMoney   = 10.0; // Account currency; 0 disables

input group "DASHBOARD"
input bool   InpShowDashboard          = true;

int hFast = INVALID_HANDLE;
int hSlow = INVALID_HANDLE;
int hADX  = INVALID_HANDLE;
int hATR  = INVALID_HANDLE;
datetime lastBarTime = 0;
int lastSignal = 0;
string statusText = "INITIALIZING";

struct BasketInfo
{
   int count;
   int buys;
   int sells;
   double floating;
   double latestBuy;
   double latestSell;
};

bool ReadOne(int handle,int buffer,int shift,double &value)
{
   double a[];
   ArraySetAsSeries(a,true);
   if(CopyBuffer(handle,buffer,shift,1,a)!=1) return false;
   value=a[0];
   return true;
}

double NormalizePrice(double price)
{
   double tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tickSize<=0.0) tickSize=_Point;
   return NormalizeDouble(MathRound(price/tickSize)*tickSize,_Digits);
}

bool GetBasket(BasketInfo &b)
{
   b.count=0; b.buys=0; b.sells=0; b.floating=0.0;
   b.latestBuy=0.0; b.latestSell=0.0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double openPrice=PositionGetDouble(POSITION_PRICE_OPEN);
      b.count++;
      b.floating+=PositionGetDouble(POSITION_PROFIT)+PositionGetDouble(POSITION_SWAP);
      if(type==POSITION_TYPE_BUY)
      {
         b.buys++;
         if(openPrice>b.latestBuy) b.latestBuy=openPrice;
      }
      else if(type==POSITION_TYPE_SELL)
      {
         b.sells++;
         if(b.latestSell==0.0 || openPrice<b.latestSell) b.latestSell=openPrice;
      }
   }
   return true;
}

double TodayClosedProfit()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(),dt);
   dt.hour=0; dt.min=0; dt.sec=0;
   datetime from=StructToTime(dt);
   if(!HistorySelect(from,TimeCurrent())) return 0.0;
   double total=0.0;
   int deals=HistoryDealsTotal();
   for(int i=0;i<deals;i++)
   {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0) continue;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol) continue;
      if((ulong)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic) continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY || entry==DEAL_ENTRY_INOUT)
         total+=HistoryDealGetDouble(deal,DEAL_PROFIT)+HistoryDealGetDouble(deal,DEAL_SWAP)+HistoryDealGetDouble(deal,DEAL_COMMISSION);
   }
   return total;
}

bool DailyLossBlocked(const BasketInfo &b)
{
   if(InpDailyLossLimitMoney<=0.0) return false;
   return (TodayClosedProfit()+b.floating)<=-InpDailyLossLimitMoney;
}

bool FiltersPass(int direction,string &reason)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) { reason="NO MARKET TICK"; return false; }
   double spread=(tick.ask-tick.bid)/_Point;
   if(spread>InpMaxSpreadPoints) { reason="SPREAD FILTER"; return false; }

   double adx=0.0,atr=0.0;
   if(!ReadOne(hADX,0,1,adx) || !ReadOne(hATR,0,1,atr))
   { reason="WAITING FOR INDICATORS"; return false; }
   if(adx<InpMinADX) { reason="NOISE FILTER: ADX LOW"; return false; }
   if(atr<InpMinATRPrice || atr>InpMaxATRPrice)
   { reason="NOISE FILTER: ATR OUTSIDE RANGE"; return false; }

   double fast1=0.0,slow1=0.0;
   if(!ReadOne(hFast,0,1,fast1) || !ReadOne(hSlow,0,1,slow1))
   { reason="WAITING FOR EMA"; return false; }
   if(direction>0 && fast1<=slow1) { reason="BUY TREND NOT CONFIRMED"; return false; }
   if(direction<0 && fast1>=slow1) { reason="SELL TREND NOT CONFIRMED"; return false; }
   reason="FILTERS PASSED";
   return true;
}

int GetFreshCross()
{
   double f1=0.0,f2=0.0,s1=0.0,s2=0.0;
   if(!ReadOne(hFast,0,1,f1) || !ReadOne(hFast,0,2,f2) ||
      !ReadOne(hSlow,0,1,s1) || !ReadOne(hSlow,0,2,s2)) return 0;
   if(f2<=s2 && f1>s1) return 1;
   if(f2>=s2 && f1<s1) return -1;
   return 0;
}

bool OpenTrade(int direction)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double sl=0.0;
   bool result=false;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   if(direction>0)
   {
      sl=NormalizePrice(tick.ask-InpInitialStopPrice);
      result=trade.Buy(InpLots,_Symbol,0.0,sl,0.0,"Gold M1 step-buy");
   }
   else
   {
      sl=NormalizePrice(tick.bid+InpInitialStopPrice);
      result=trade.Sell(InpLots,_Symbol,0.0,sl,0.0,"Gold M1 step-sell");
   }
   if(!result)
      Print("Entry failed. Retcode=",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
   return result;
}

void ManageIndividualTrails()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   int stopLevel=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   double minDistance=stopLevel*_Point;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol ||
         (ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;

      ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double open=PositionGetDouble(POSITION_PRICE_OPEN);
      double oldSL=PositionGetDouble(POSITION_SL);
      double tp=PositionGetDouble(POSITION_TP);
      double candidate=0.0;

      if(type==POSITION_TYPE_BUY)
      {
         double move=tick.bid-open;
         if(move<InpTrailStartPrice) continue;
         candidate=NormalizePrice(tick.bid-InpTrailDistancePrice);
         if(tick.bid-candidate<minDistance) continue;
         if(oldSL==0.0 || candidate>oldSL+_Point)
         {
            if(!trade.PositionModify(ticket,candidate,tp))
               Print("Trail modify failed ticket ",ticket,": ",trade.ResultRetcodeDescription());
         }
      }
      else if(type==POSITION_TYPE_SELL)
      {
         double move=open-tick.ask;
         if(move<InpTrailStartPrice) continue;
         candidate=NormalizePrice(tick.ask+InpTrailDistancePrice);
         if(candidate-tick.ask<minDistance) continue;
         if(oldSL==0.0 || candidate<oldSL-_Point)
         {
            if(!trade.PositionModify(ticket,candidate,tp))
               Print("Trail modify failed ticket ",ticket,": ",trade.ResultRetcodeDescription());
         }
      }
   }
}

void UpdateDashboard(const BasketInfo &b)
{
   if(!InpShowDashboard) { Comment(""); return; }
   MqlTick tick;
   SymbolInfoTick(_Symbol,tick);
   double adx=0.0,atr=0.0;
   ReadOne(hADX,0,1,adx);
   ReadOne(hATR,0,1,atr);
   double day=TodayClosedProfit()+b.floating;
   string mode=(b.buys>0 ? "BUY ONLY" : (b.sells>0 ? "SELL ONLY" : "WAITING"));
   Comment("GOLD M1 MICRO-SCALPER  |  ",_Symbol,
           "\nSTATUS: ",statusText,
           "\nMODE: ",mode,"     OPEN: ",b.count," / ",InpMaxTrades,
           "\nBUY: ",b.buys,"     SELL: ",b.sells,
           "\nFLOATING P/L: ",DoubleToString(b.floating,2),
           "     TODAY: ",DoubleToString(day,2),
           "\nADX: ",DoubleToString(adx,1),"     ATR: ",DoubleToString(atr,_Digits),
           "     SPREAD: ",DoubleToString((tick.ask-tick.bid)/_Point,1),
           "\nNEXT ENTRY STEP: ",DoubleToString(InpEntryStepPrice,2),
           " price units     TRAIL: ",DoubleToString(InpTrailStartPrice,2),
           " / ",DoubleToString(InpTrailDistancePrice,2));
}

int OnInit()
{
   if(_Period!=PERIOD_M1)
      Print("NOTICE: This EA is designed for the M1 chart.");
   if(InpMaxTrades<1 || InpMaxTrades>10 || InpLots<=0.0 ||
      InpEntryStepPrice<=0.0 || InpInitialStopPrice<=0.0 ||
      InpTrailStartPrice<=0.0 || InpTrailDistancePrice<=0.0)
      return INIT_PARAMETERS_INCORRECT;

   hFast=iMA(_Symbol,PERIOD_M1,InpFastEMA,0,MODE_EMA,PRICE_CLOSE);
   hSlow=iMA(_Symbol,PERIOD_M1,InpSlowEMA,0,MODE_EMA,PRICE_CLOSE);
   hADX=iADX(_Symbol,PERIOD_M1,InpADXPeriod);
   hATR=iATR(_Symbol,PERIOD_M1,InpATRPeriod);
   if(hFast==INVALID_HANDLE || hSlow==INVALID_HANDLE ||
      hADX==INVALID_HANDLE || hATR==INVALID_HANDLE)
   {
      Print("Failed to create indicator handles.");
      return INIT_FAILED;
   }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   lastBarTime=iTime(_Symbol,PERIOD_M1,0);
   statusText="READY - WAITING FOR EMA CROSS";
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(hFast!=INVALID_HANDLE) IndicatorRelease(hFast);
   if(hSlow!=INVALID_HANDLE) IndicatorRelease(hSlow);
   if(hADX!=INVALID_HANDLE) IndicatorRelease(hADX);
   if(hATR!=INVALID_HANDLE) IndicatorRelease(hATR);
   Comment("");
}

void OnTick()
{
   BasketInfo basket;
   GetBasket(basket);
   ManageIndividualTrails();

   if(DailyLossBlocked(basket))
   {
      statusText="DAILY LOSS LIMIT - ENTRIES PAUSED";
      UpdateDashboard(basket);
      return;
   }

   datetime bar=iTime(_Symbol,PERIOD_M1,0);
   if(bar!=0 && bar!=lastBarTime)
   {
      lastBarTime=bar;
      int cross=GetFreshCross();
      if(cross!=0) lastSignal=cross;
   }

   string reason="";
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) { statusText="WAITING FOR PRICE"; UpdateDashboard(basket); return; }

   if(basket.count>=InpMaxTrades)
      statusText="MAX POSITIONS REACHED";
   else if(basket.buys>0 && basket.sells>0)
      statusText="SAFETY HOLD: MIXED DIRECTIONS DETECTED";
   else if(basket.count==0)
   {
      int direction=lastSignal;
      if(direction==0) statusText="WAITING FOR FRESH EMA CROSS";
      else if((direction>0 && !InpAllowBuy) || (direction<0 && !InpAllowSell))
         statusText="SIGNAL DISABLED BY INPUT";
      else if(!FiltersPass(direction,reason)) statusText=reason;
      else
      {
         if(OpenTrade(direction))
         {
            statusText=(direction>0 ? "BUY OPENED - WAIT FOR NEXT STEP" : "SELL OPENED - WAIT FOR NEXT STEP");
            GetBasket(basket);
         }
         else statusText="ORDER REJECTED - CHECK JOURNAL";
      }
   }
   else if(basket.buys>0)
   {
      if(!FiltersPass(1,reason)) statusText=reason+" - NO ADD-ON";
      else if(tick.bid>=basket.latestBuy+InpEntryStepPrice)
      {
         if(OpenTrade(1)) { statusText="BUY STEP FILLED"; GetBasket(basket); }
         else statusText="BUY STEP REJECTED";
      }
      else statusText="BUY RUNNING - WAITING FOR +"+DoubleToString(InpEntryStepPrice,2);
   }
   else if(basket.sells>0)
   {
      if(!FiltersPass(-1,reason)) statusText=reason+" - NO ADD-ON";
      else if(tick.ask<=basket.latestSell-InpEntryStepPrice)
      {
         if(OpenTrade(-1)) { statusText="SELL STEP FILLED"; GetBasket(basket); }
         else statusText="SELL STEP REJECTED";
      }
      else statusText="SELL RUNNING - WAITING FOR -"+DoubleToString(InpEntryStepPrice,2);
   }
   UpdateDashboard(basket);
}
//+------------------------------------------------------------------+
