/*
 * epwm.c
 *
 *  Created on: 2018-1-26
 *      Author: Administrator
 */


#include "epwm.h"
#include "leds.h"


void EPWM1_Init(Uint16 tbprd)
{
	EALLOW;
	SysCtrlRegs.PCLKCR0.bit.TBCLKSYNC = 1;   // Disable TBCLK within the ePWM
	SysCtrlRegs.PCLKCR1.bit.EPWM1ENCLK = 1;  // ePWM1
	EDIS;

	// Interrupts that are used in this example are re-mapped to
	// ISR functions found within this file.
	EALLOW;  // This is needed to write to EALLOW protected registers
	PieVectTable.EPWM1_INT = &epwm1_timer_isr;
	EDIS;    // This is needed to disable write to EALLOW protected registers

	EALLOW;
	SysCtrlRegs.PCLKCR0.bit.TBCLKSYNC = 0;      // Stop all the TB clocks
	EDIS;

	// Setup Sync
	EPwm1Regs.TBCTL.bit.SYNCOSEL = TB_SYNC_IN;  // Pass through

	// Allow each timer to be sync'ed
	EPwm1Regs.TBCTL.bit.PHSEN = TB_ENABLE;

	EPwm1Regs.TBPHS.half.TBPHS = 0;

	EPwm1Regs.TBPRD = tbprd;
	EPwm1Regs.TBCTL.bit.CTRMODE = TB_COUNT_UP;    // Count up
	EPwm1Regs.TBCTL.bit.HSPCLKDIV=TB_DIV1;
	EPwm1Regs.TBCTL.bit.CLKDIV=TB_DIV1;
	EPwm1Regs.ETSEL.bit.INTSEL = ET_CTR_ZERO;     // Select INT on Zero event
	EPwm1Regs.ETSEL.bit.INTEN = 1;  // Enable INT
	EPwm1Regs.ETPS.bit.INTPRD = ET_1ST;           // Generate INT on 1st event

	EALLOW;
	SysCtrlRegs.PCLKCR0.bit.TBCLKSYNC = 1;         // Start all the timers synced
	EDIS;

	// Enable CPU INT3 which is connected to EPWM1-6 INT:
	IER |= M_INT3;

	// Enable EPWM INTn in the PIE: Group 3 interrupt 1-6
	PieCtrlRegs.PIEIER3.bit.INTx1 = 1;

	// Enable global Interrupts and higher priority real-time debug events:
	EINT;   // Enable Global interrupt INTM
	ERTM;   // Enable Global realtime interrupt DBGM
}

interrupt void epwm1_timer_isr(void)
{
	static Uint16 cnt=0;

	cnt++;
	if(cnt==5000)
	{
		cnt=0;
		LED3_TOGGLE;
	}

	// Clear INT flag for this timer
	EPwm1Regs.ETCLR.bit.INT = 1;
	// Acknowledge this interrupt to receive more interrupts from group 3
	PieCtrlRegs.PIEACK.bit.ACK3 = 1;
}

