/*
 * adc.c
 *
 *  Created on: 2018-1-29
 *      Author: Administrator
 */

#include "adc.h"



// Global variable for this example
Uint16 SampleTable[BUF_SIZE]={0};


void ADC_Init(void)
{
	EALLOW;
	SysCtrlRegs.PCLKCR0.bit.ADCENCLK = 1;    // ADC
	SysCtrlRegs.PCLKCR0.bit.TBCLKSYNC = 1;   // Disable TBCLK within the ePWM
	SysCtrlRegs.PCLKCR1.bit.EPWM1ENCLK = 1;  // ePWM1
	EDIS;

	// Specific clock setting for this example:
	EALLOW;
	SysCtrlRegs.HISPCP.all = ADC_MODCLK;	// HSPCLK = SYSCLKOUT/2*ADC_MODCLK
	EDIS;

	// Interrupts that are used in this example are re-mapped to
	// ISR functions found within this file.
	EALLOW;  // This is needed to write to EALLOW protected register
	PieVectTable.ADCINT = &adc_isr;
	EDIS;    // This is needed to disable write to EALLOW protected registers

	InitAdc();  // For this example, init the ADC

	// Enable ADCINT in PIE
	PieCtrlRegs.PIEIER1.bit.INTx6 = 1;
	IER |= M_INT1; // Enable CPU Interrupt 1
	EINT;          // Enable Global interrupt INTM
	ERTM;          // Enable Global realtime interrupt DBGM


	AdcRegs.ADCTRL1.bit.SEQ_OVRD = 1;       // Enable Sequencer override feature
	AdcRegs.ADCCHSELSEQ1.bit.CONV00 = 0x0; // Setup ADCINA0 as 1st SEQ1 conv.
	AdcRegs.ADCCHSELSEQ1.bit.CONV01 = 0x1;// Setup ADCINA1 as 2nd SEQ1 conv.
	AdcRegs.ADCMAXCONV.bit.MAX_CONV1= 0x1;  // Setup 2 conv's on SEQ1
	AdcRegs.ADCTRL2.bit.EPWM_SOCA_SEQ1 = 1;// Enable SOCA from ePWM to start SEQ1
	AdcRegs.ADCTRL2.bit.INT_ENA_SEQ1 = 1;  // Enable SEQ1 interrupt (every EOS)

	// Assumes ePWM1 clock is already enabled in InitSysCtrl();
	EPwm1Regs.ETSEL.bit.SOCAEN = 1;        // Enable SOC on A group
	EPwm1Regs.ETSEL.bit.SOCASEL = 4;       // Select SOC from from CPMA on upcount
	EPwm1Regs.ETPS.bit.SOCAPRD = 1;        // Generate pulse on 1st event
	EPwm1Regs.CMPA.half.CMPA = 0x0080;	  // Set compare A value
	EPwm1Regs.TBPRD = 0xFFFF;              // Set period for ePWM1
	EPwm1Regs.TBCTL.bit.CTRMODE = 0;		  // count up and start

}

interrupt void  adc_isr(void)
{
	static Uint16 i=0;
	i++;

	AdcRegs.ADCTRL2.bit.RST_SEQ1 = 1;         // Reset SEQ1
	if(i==1000)
	{
		i=0;
		SampleTable[0]= ( (AdcRegs.ADCRESULT0)>>4);
		SampleTable[1]= ( (AdcRegs.ADCRESULT1)>>4);
	}

  // Reinitialize for next ADC sequence
	AdcRegs.ADCST.bit.INT_SEQ1_CLR = 1;       // Clear INT SEQ1 bit
	PieCtrlRegs.PIEACK.bit.ACK1 = 1;   // Acknowledge interrupt to PIE
}

Uint16 Read_ADC_CH0_Value(void)
{
	while (AdcRegs.ADCST.bit.INT_SEQ1== 0);
	AdcRegs.ADCST.bit.INT_SEQ1_CLR = 1;
	return AdcRegs.ADCRESULT0>>4;
}


void Read_ADC_SEQ1_Value_OVD(void)
{
	Uint16 array_index=0;

	while (AdcRegs.ADCST.bit.INT_SEQ1== 0);
	AdcRegs.ADCST.bit.INT_SEQ1_CLR = 1;

	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT0)>>4);
	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT1)>>4);
	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT2)>>4);
	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT3)>>4);
	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT4)>>4);
	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT5)>>4);
	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT6)>>4);
	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT7)>>4);

	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT8)>>4);
	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT9)>>4);
	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT10)>>4);
	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT11)>>4);
	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT12)>>4);
	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT13)>>4);
	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT14)>>4);
	SampleTable[array_index++]= ( (AdcRegs.ADCRESULT15)>>4);
}
