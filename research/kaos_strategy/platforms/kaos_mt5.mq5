//+------------------------------------------------------------------+
//| kaos_mt5.mq5 - KAOS Strategy v1 for MetaTrader 5                 |
//|                                                                  |
//| Same rules as spec.md: Kaufman efficiency-ratio regime split,     |
//| PULSE mean reversion inside a range, 3.0 ATR target, 5.0 ATR stop |
//| and a 24-bar expiry. Parameters are bars/ATR only, so the EA runs |
//| unchanged on M5 through H4.                                      |
//|                                                                  |
//| Risk is fixed per trade: lots = risk% * equity / (stop distance   |
//| in price * tick value), so a 5 ATR stop risks the same money on   |
//| EURUSD M5 and on BTCUSD H1.                                       |
//+------------------------------------------------------------------+
#property copyright "KAOS"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
CTrade trade;

//--- inputs
input group            "Regime"
input int              InpErLen        = 20;
input double           InpErRangeMax    = 0.28;
input double           InpErTrendMin    = 0.30;
input group            "Indicators"
input int              InpEmaFast       = 20;
input int              InpEmaSlow       = 50;
input int              InpAtrLen        = 14;
input int              InpRsiLen        = 14;
input int              InpBbLen         = 20;
input double           InpBbSd          = 2.0;
input group            "PULSE"
input double           InpZEntry        = 1.0;
input double           InpRsiPulse      = 42.0;
input double           InpKnifeGuard    = 2.0;
input double           InpTpAtr         = 3.0;
input double           InpSlAtr         = 5.0;
input int              InpMaxBars       = 24;
input group            "DRIVE"
input bool             InpUseDrive      = false;
input double           InpDrTpAtr       = 1.6;
input double           InpDrSlAtr       = 1.0;
input int              InpDrMaxBars     = 24;
input group            "Risk"
input double           InpRiskPercent   = 0.5;      // % of equity risked per trade
input long             InpMagic         = 20261119;
input int              InpSlippage      = 10;

//--- handles and state
int    hAtr, hEmaFast, hEmaSlow, hRsi, hBands;
datetime lastBarTime = 0;
int    entryBarIndex = -1;      // bar index at entry, for the bar-counted expiry

//+------------------------------------------------------------------+
int OnInit()
{
   hAtr     = iATR(_Symbol, _Period, InpAtrLen);
   hEmaFast = iMA(_Symbol, _Period, InpEmaFast, 0, MODE_EMA, PRICE_CLOSE);
   hEmaSlow = iMA(_Symbol, _Period, InpEmaSlow, 0, MODE_EMA, PRICE_CLOSE);
   hRsi     = iRSI(_Symbol, _Period, InpRsiLen, PRICE_CLOSE);
   hBands   = iBands(_Symbol, _Period, InpBbLen, 0, InpBbSd, PRICE_CLOSE);
   if(hAtr == INVALID_HANDLE || hEmaFast == INVALID_HANDLE || hEmaSlow == INVALID_HANDLE ||
      hRsi == INVALID_HANDLE || hBands == INVALID_HANDLE)
   {
      Print("KAOS: indicator handle creation failed");
      return INIT_FAILED;
   }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippage);
   PrintFormat("KAOS v1 attached to %s %s", _Symbol, EnumToString(_Period));
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(hAtr     != INVALID_HANDLE) IndicatorRelease(hAtr);
   if(hEmaFast != INVALID_HANDLE) IndicatorRelease(hEmaFast);
   if(hEmaSlow != INVALID_HANDLE) IndicatorRelease(hEmaSlow);
   if(hRsi     != INVALID_HANDLE) IndicatorRelease(hRsi);
   if(hBands   != INVALID_HANDLE) IndicatorRelease(hBands);
}

//+------------------------------------------------------------------+
//| Efficiency ratio over InpErLen bars, computed on closed bars      |
//+------------------------------------------------------------------+
double EfficiencyRatio()
{
   double net  = MathAbs(iClose(_Symbol, _Period, 1) - iClose(_Symbol, _Period, 1 + InpErLen));
   double path = 0.0;
   for(int i = 1; i <= InpErLen; i++)
      path += MathAbs(iClose(_Symbol, _Period, i) - iClose(_Symbol, _Period, i + 1));
   if(path <= 0.0) return 0.0;
   double er = net / path;
   return MathMin(MathMax(er, 0.0), 1.0);
}

//+------------------------------------------------------------------+
bool HasPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
double LotsForRisk(double stopDistancePrice)
{
   double equity   = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskCash = equity * InpRiskPercent / 100.0;
   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickVal <= 0.0 || tickSize <= 0.0 || stopDistancePrice <= 0.0) return 0.0;

   double lossPerLot = (stopDistancePrice / tickSize) * tickVal;
   if(lossPerLot <= 0.0) return 0.0;
   double lots = riskCash / lossPerLot;

   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lots = MathFloor(lots / lotStep) * lotStep;
   lots = MathMin(MathMax(lots, minLot), maxLot);
   return NormalizeDouble(lots, 2);
}

//+------------------------------------------------------------------+
void OnTick()
{
   // decide once per closed bar
   datetime barTime = iTime(_Symbol, _Period, 0);
   if(barTime == lastBarTime) return;
   lastBarTime = barTime;

   double atr[1], emaF[1], emaS[1], rsi[1], bbUp[1], bbLo[1];
   if(CopyBuffer(hAtr, 0, 1, 1, atr)   <= 0) return;
   if(CopyBuffer(hEmaFast, 0, 1, 1, emaF) <= 0) return;
   if(CopyBuffer(hEmaSlow, 0, 1, 1, emaS) <= 0) return;
   if(CopyBuffer(hRsi, 0, 1, 1, rsi)   <= 0) return;
   if(CopyBuffer(hBands, 1, 1, 1, bbUp) <= 0) return;   // upper band
   if(CopyBuffer(hBands, 2, 1, 1, bbLo) <= 0) return;   // lower band

   double close1 = iClose(_Symbol, _Period, 1);
   double open1  = iOpen(_Symbol, _Period, 1);
   double high1  = iHigh(_Symbol, _Period, 1);
   double low1   = iLow(_Symbol, _Period, 1);
   double a      = atr[0];
   if(a <= 0.0) return;

   double z     = (close1 - emaF[0]) / a;
   double zSlow = (close1 - emaS[0]) / a;
   double er    = EfficiencyRatio();
   double erPrev = 0.0;
   {
      // previous ER value for the DRIVE slope test
      double net  = MathAbs(iClose(_Symbol, _Period, 2) - iClose(_Symbol, _Period, 2 + InpErLen));
      double path = 0.0;
      for(int i = 2; i <= InpErLen + 1; i++)
         path += MathAbs(iClose(_Symbol, _Period, i) - iClose(_Symbol, _Period, i + 1));
      erPrev = (path > 0.0) ? MathMin(MathMax(net / path, 0.0), 1.0) : 0.0;
   }
   double erSlope = er - erPrev;

   bool trend  = (er >= InpErTrendMin) && (MathAbs(zSlow) > 0.5);
   bool up     = trend && (emaF[0] > emaS[0]);
   bool down   = trend && (emaF[0] < emaS[0]);
   bool range  = (er <= InpErRangeMax);

   bool pulseLong  = range && (z <= -InpZEntry) && (rsi[0] <= InpRsiPulse) &&
                     (close1 < bbLo[0]) && (zSlow > -InpKnifeGuard);
   bool pulseShort = range && (z >=  InpZEntry) && (rsi[0] >= 100.0 - InpRsiPulse) &&
                     (close1 > bbUp[0]) && (zSlow <  InpKnifeGuard);

   bool driveLong  = InpUseDrive && up   && (low1  <= emaF[0]) && (close1 > emaF[0]) &&
                     (close1 > open1) && (erSlope > 0);
   bool driveShort = InpUseDrive && down && (high1 >= emaF[0]) && (close1 < emaF[0]) &&
                     (close1 < open1) && (erSlope > 0);

   //--- bar-counted expiry on the open position
   if(HasPosition())
   {
      int maxBars = (pulseLong || pulseShort) ? InpMaxBars : InpDrMaxBars;
      if(entryBarIndex >= 0 && Bars(_Symbol, _Period) - entryBarIndex >= maxBars)
      {
         trade.PositionClose(_Symbol);
         entryBarIndex = -1;
      }
      return;                                  // one position at a time
   }

   if(!pulseLong && !pulseShort && !driveLong && !driveShort) return;

   bool isLong = pulseLong || driveLong;
   double tpMult = (pulseLong || pulseShort) ? InpTpAtr : InpDrTpAtr;
   double slMult = (pulseLong || pulseShort) ? InpSlAtr : InpDrSlAtr;

   double price = isLong ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double stop  = isLong ? price - slMult * a : price + slMult * a;
   double limit = isLong ? price + tpMult * a : price - tpMult * a;

   double lots = LotsForRisk(slMult * a);
   if(lots <= 0.0)
   {
      Print("KAOS: sizing returned zero lots, skipping");
      return;
   }

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   stop  = NormalizeDouble(stop,  digits);
   limit = NormalizeDouble(limit, digits);

   bool ok = isLong ? trade.Buy(lots, _Symbol, 0.0, stop, limit, "KAOS long")
                    : trade.Sell(lots, _Symbol, 0.0, stop, limit, "KAOS short");
   if(ok)
   {
      entryBarIndex = Bars(_Symbol, _Period);
      PrintFormat("KAOS %s %s lots=%.2f atr=%.5f stop=%.5f target=%.5f expiry=%d bars",
                  _Symbol, (isLong ? "long" : "short"), lots, a, stop, limit,
                  (pulseLong || pulseShort) ? InpMaxBars : InpDrMaxBars);
   }
   else
   {
      PrintFormat("KAOS: order failed retcode=%d %s", trade.ResultRetcode(),
                  trade.ResultRetcodeDescription());
   }
}
//+------------------------------------------------------------------+
