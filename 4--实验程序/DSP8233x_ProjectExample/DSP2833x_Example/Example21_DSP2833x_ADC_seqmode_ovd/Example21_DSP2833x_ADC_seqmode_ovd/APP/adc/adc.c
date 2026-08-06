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
	EDIS;

	// Specific clock setting for this example:
	EALLOW;
	SysCtrlRegs.HISPCP.all = ADC_MODCLK;	// HSPCLK = SYSCLKOUT/2*ADC_MODCLK
	EDIS;

	InitAdc();  // For this example, init the ADC

	// Specific ADC setup for this example:
	AdcRegs.ADCTRL1.bit.ACQ_PS = ADC_SHCLK;  //Sequential mode: Sample rate   = 1/[(2+ACQ_PS)*ADC clock in ns]
	                        //                  = 1/(3*40ns) =8.3MHz (for 150 MHz SYSCLKOUT)
						    //                  = 1/(3*80ns) =4.17MHz (for 100 MHz SYSCLKOUT)
						    // If Simultaneous mode enabled: Sample rate = 1/[(3+ACQ_PS)*ADC clock in ns]
	AdcRegs.ADCTRL3.bit.ADCCLKPS = ADC_CKPS;
	AdcRegs.ADCTRL1.bit.SEQ_CASC = 1;        // 1  Cascaded mode
	AdcRegs.ADCCHSELSEQ1.bit.CONV00 = 0x0;
	AdcRegs.ADCTRL1.bit.CONT_RUN = 1;       // Setup continuous run


	AdcRegs.ADCTRL1.bit.SEQ_OVRD = 1;       // Enable Sequencer override feature
	AdcRegs.ADCCHSELSEQ1.all = 0x0;         // Initialize all ADC channel selects to A0
	AdcRegs.ADCCHSELSEQ2.all = 0x0;
	AdcRegs.ADCCHSELSEQ3.all = 0x0;
	AdcRegs.ADCCHSELSEQ4.all = 0x0;
	AdcRegs.ADCMAXCONV.bit.MAX_CONV1 = 0x7;  // convert and store in 8 results registers

	// Start SEQ1
	AdcRegs.ADCTRL2.all = 0x2000;

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
