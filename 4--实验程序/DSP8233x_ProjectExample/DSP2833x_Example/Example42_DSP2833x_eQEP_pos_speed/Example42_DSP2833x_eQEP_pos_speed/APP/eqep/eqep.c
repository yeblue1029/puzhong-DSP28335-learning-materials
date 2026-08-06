/*
 * eqep.c
 *
 *  Created on: 2018Äê7ÔÂ12ÈÕ
 *      Author: Administrator
 */

#include "eqep.h"
#include "Example_posspeed.h"


POSSPEED qep_posspeed=POSSPEED_DEFAULTS;
Uint16 Interrupt_Count = 0;

interrupt void prdTick(void);


#if (CPU_FRQ_150MHZ)
  #define CPU_CLK   150e6
#endif
#if (CPU_FRQ_100MHZ)
  #define CPU_CLK   100e6
#endif

#define PWM_CLK   5e3              // 5kHz (300rpm) EPWM1 frequency. Freq. can be changed here
#define SP        CPU_CLK/(2*PWM_CLK)
#define TBCTLVAL  0x200E           // up-down count, timebase=SYSCLKOUT


void EPwm1Setup(void)
{
    InitEPwm1Gpio();

    EALLOW;
	GpioCtrlRegs.GPADIR.bit.GPIO4 = 1;    // GPIO4 as output simulates Index signal
	GpioDataRegs.GPACLEAR.bit.GPIO4 = 1;  // Normally low
	EDIS;

	EPwm1Regs.TBSTS.all=0;
	EPwm1Regs.TBPHS.half.TBPHS =0;
	EPwm1Regs.TBCTR=0;

	EPwm1Regs.CMPCTL.all=0x50;     // immediate mode for CMPA and CMPB
	EPwm1Regs.CMPA.half.CMPA=SP/2;
	EPwm1Regs.CMPB=0;

	EPwm1Regs.AQCTLA.all=0x60;     // CTR=CMPA when inc->EPWM1A=1, when dec->EPWM1A=0
	EPwm1Regs.AQCTLB.all=0x09;     // CTR=PRD ->EPWM1B=1, CTR=0 ->EPWM1B=0
	EPwm1Regs.AQSFRC.all=0;
	EPwm1Regs.AQCSFRC.all=0;

	EPwm1Regs.TZSEL.all=0;
	EPwm1Regs.TZCTL.all=0;
	EPwm1Regs.TZEINT.all=0;
	EPwm1Regs.TZFLG.all=0;
	EPwm1Regs.TZCLR.all=0;
	EPwm1Regs.TZFRC.all=0;

	EPwm1Regs.ETSEL.all=0x0A;      // Interrupt on PRD
	EPwm1Regs.ETPS.all=1;
	EPwm1Regs.ETFLG.all=0;
	EPwm1Regs.ETCLR.all=0;
	EPwm1Regs.ETFRC.all=0;

	EPwm1Regs.PCCTL.all=0;

	EPwm1Regs.TBCTL.all=0x0010+TBCTLVAL; // Enable Timer
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

	qep_posspeed.init(&qep_posspeed);
}

interrupt void prdTick(void)                  // EPWM1 Interrupts once every 4 QCLK counts (one period)
{
	Uint16 i;
	// Position and Speed measurement
	qep_posspeed.calc(&qep_posspeed);

	// Control loop code for position control & Speed contol
	Interrupt_Count++;
	if (Interrupt_Count==1000)                 // Every 1000 interrupts(4000 QCLK counts or 1 rev.)
	{
		EALLOW;
		GpioDataRegs.GPASET.bit.GPIO4 = 1;     // Pulse Index signal  (1 pulse/rev.)
		for (i=0; i<700; i++){
	}
	GpioDataRegs.GPACLEAR.bit.GPIO4 = 1;
	Interrupt_Count = 0;                   // Reset count
	EDIS;
	}

	// Acknowledge this interrupt to receive more interrupts from group 1
	PieCtrlRegs.PIEACK.all = PIEACK_GROUP3;
	EPwm1Regs.ETCLR.bit.INT=1;
}

