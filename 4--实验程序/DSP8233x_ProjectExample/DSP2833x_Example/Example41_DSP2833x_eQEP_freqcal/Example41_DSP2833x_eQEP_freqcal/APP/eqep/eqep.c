/*
 * eqep.c
 *
 *  Created on: 2018Äê7ÔÂ12ÈÕ
 *      Author: Administrator
 */

#include "eqep.h"
#include "Example_freqcal.h"


FREQCAL freq=FREQCAL_DEFAULTS;

interrupt void prdTick(void);


#if (CPU_FRQ_150MHZ)
  #define CPU_CLK   150e6
#endif
#if (CPU_FRQ_100MHZ)
  #define CPU_CLK   100e6
#endif
#define PWM_CLK   5e3                 // If diff freq. desired, change freq here.
#define SP        CPU_CLK/(2*PWM_CLK)
#define TBCTLVAL  0x200E              // Up-down cnt, timebase = SYSCLKOUT


void EPwm1Setup(void)
{
    InitEPwm1Gpio();
	EPwm1Regs.TBSTS.all=0;
	EPwm1Regs.TBPHS.half.TBPHS=0;
	EPwm1Regs.TBCTR=0;

	EPwm1Regs.CMPCTL.all=0x50;        // Immediate mode for CMPA and CMPB
	EPwm1Regs.CMPA.half.CMPA =SP/2;
	EPwm1Regs.CMPB=0;

	EPwm1Regs.AQCTLA.all=0x60;        // EPWMxA = 1 when CTR=CMPA and counter inc
	                                  // EPWMxA = 0 when CTR=CMPA and counter dec
	EPwm1Regs.AQCTLB.all=0;
	EPwm1Regs.AQSFRC.all=0;
	EPwm1Regs.AQCSFRC.all=0;

	EPwm1Regs.DBCTL.all=0xb;          // EPWMxB is inverted
	EPwm1Regs.DBRED=0;
	EPwm1Regs.DBFED=0;

	EPwm1Regs.TZSEL.all=0;
	EPwm1Regs.TZCTL.all=0;
	EPwm1Regs.TZEINT.all=0;
	EPwm1Regs.TZFLG.all=0;
	EPwm1Regs.TZCLR.all=0;
	EPwm1Regs.TZFRC.all=0;

	EPwm1Regs.ETSEL.all=9;            // Interrupt when TBCTR = 0x0000
	EPwm1Regs.ETPS.all=1;	          // Interrupt on first event
	EPwm1Regs.ETFLG.all=0;
	EPwm1Regs.ETCLR.all=0;
	EPwm1Regs.ETFRC.all=0;

	EPwm1Regs.PCCTL.all=0;

	EPwm1Regs.TBCTL.all=0x0010+TBCTLVAL;			// Enable Timer
	EPwm1Regs.TBPRD=SP;

	EALLOW;  // This is needed to write to EALLOW protected registers
	PieVectTable.EPWM1_INT= &prdTick;
	EDIS;

	IER |= M_INT3;
	PieCtrlRegs.PIEIER3.bit.INTx1 = 1;
	EINT;   // Enable Global interrupt INTM
	ERTM;   // Enable Global realtime interrupt DBGM

}



void EQEP1_Init(void)
{
	EALLOW;  // This is needed to write to EALLOW protected registers
	SysCtrlRegs.PCLKCR1.bit.EQEP1ENCLK = 1;  // eQEP1
	EDIS;

	InitEQep1Gpio();

	EPwm1Setup();

	freq.init();   // Initializes eQEP for frequency calculation in
						// FREQCAL_Init(void)function in Example_EPwmSetup.c
}

interrupt void prdTick(void) // Interrupts once per ePWM period
{
   freq.calc(&freq); // Checks for event and calculates frequency in FREQCAL_Calc(FREQCAL *p)
                     // function in Example_EPwmSetup.c
   // Acknowledge this interrupt to receive more interrupts from group 1
   PieCtrlRegs.PIEACK.all = PIEACK_GROUP3;
   EPwm1Regs.ETCLR.bit.INT=1;
}

