/*
 * adc.c
 *
 *  Created on: 2018-1-29
 *      Author: Administrator
 */

#include "adc.h"


#define ADC_MODCLK 3
#define ADC_CKPS   0x1   // ADC module clock = HSPCLK/2*ADC_CKPS   = 25.0MHz/(1*2) = 12.5MHz
#define ADC_SHCLK  0xf   // S/H width in ADC module periods                        = 16 ADC clocks


void ADC_Init(void)
{
	EALLOW;
	SysCtrlRegs.PCLKCR0.bit.ADCENCLK = 1;    // ADC
	EDIS;

	// Specific clock setting for this example:
	EALLOW;
	SysCtrlRegs.HISPCP.all = ADC_MODCLK;	// HSPCLK = SYSCLKOUT/ADC_MODCLK
	EDIS;

	InitAdc();  // For this example, init the ADC

	// Specific ADC setup for this example:
	AdcRegs.ADCTRL1.bit.ACQ_PS = ADC_SHCLK;
	AdcRegs.ADCTRL3.bit.ADCCLKPS = ADC_CKPS;
	AdcRegs.ADCTRL1.bit.SEQ_CASC = 1;        // 1  Cascaded mode
	AdcRegs.ADCCHSELSEQ1.bit.CONV00 = 0x0;
	AdcRegs.ADCTRL1.bit.CONT_RUN = 1;       // Setup continuous run

	// Start SEQ1
	AdcRegs.ADCTRL2.all = 0x2000;

}

Uint16 Read_ADCValue(void)
{
	while (AdcRegs.ADCST.bit.INT_SEQ1== 0);
	AdcRegs.ADCST.bit.INT_SEQ1_CLR = 1;
	return AdcRegs.ADCRESULT0>>4;
}

