/*
 * dma.c
 *
 *  Created on: 2018-1-30
 *      Author: Administrator
 */


#include "dma.h"



// Configure the timing paramaters for Zone 7.
// Notes:
//    This function should not be executed from XINTF
//    Adjust the timing based on the data manual and
//    external device requirements.
void init_zone7(void)
{
	EALLOW;
    // Make sure the XINTF clock is enabled
	SysCtrlRegs.PCLKCR3.bit.XINTFENCLK = 1;
	EDIS;
	// Configure the GPIO for XINTF with a 16-bit data bus
	// This function is in DSP2833x_Xintf.c
	InitXintf16Gpio();

    // All Zones---------------------------------
    // Timing for all zones based on XTIMCLK = SYSCLKOUT
	EALLOW;
    XintfRegs.XINTCNF2.bit.XTIMCLK = 0;
    // Buffer up to 3 writes
    XintfRegs.XINTCNF2.bit.WRBUFF = 3;
    // XCLKOUT is enabled
    XintfRegs.XINTCNF2.bit.CLKOFF = 0;
    // XCLKOUT = XTIMCLK
    XintfRegs.XINTCNF2.bit.CLKMODE = 0;

    // Zone 7------------------------------------
    // When using ready, ACTIVE must be 1 or greater
    // Lead must always be 1 or greater
    // Zone write timing
    XintfRegs.XTIMING7.bit.XWRLEAD = 1;
    XintfRegs.XTIMING7.bit.XWRACTIVE = 2;
    XintfRegs.XTIMING7.bit.XWRTRAIL = 1;
    // Zone read timing
    XintfRegs.XTIMING7.bit.XRDLEAD = 1;
    XintfRegs.XTIMING7.bit.XRDACTIVE = 3;
    XintfRegs.XTIMING7.bit.XRDTRAIL = 0;

    // don't double all Zone read/write lead/active/trail timing
    XintfRegs.XTIMING7.bit.X2TIMING = 0;

    // Zone will not sample XREADY signal
    XintfRegs.XTIMING7.bit.USEREADY = 0;
    XintfRegs.XTIMING7.bit.READYMODE = 0;

    // 1,1 = x16 data bus
    // 0,1 = x32 data bus
    // other values are reserved
    XintfRegs.XTIMING7.bit.XSIZE = 3;
    EDIS;
   //Force a pipeline flush to ensure that the write to
   //the last register configured occurs before returning.
   asm(" RPT #7 || NOP");
}


void DMACH1_Init(volatile Uint16 *DMA_Dest,volatile Uint16 *DMA_Source)
{

	EALLOW;
	SysCtrlRegs.PCLKCR3.bit.DMAENCLK = 1;       // DMA Clock
	EDIS;

	EALLOW;
	SysCtrlRegs.PCLKCR3.bit.CPUTIMER0ENCLK = 1; // CPU Timer 0
	EDIS;
	CpuTimer0Regs.TCR.bit.TSS  = 1;               //Stop Timer0 for now

#ifdef DMA_INT_ENABLE
	// Interrupts that are used in this example are re-mapped to
	// ISR functions found within this file.
	EALLOW;	// Allow access to EALLOW protected registers
	PieVectTable.DINTCH1= &local_DINTCH1_ISR;
	EDIS;   // Disable access to EALLOW protected registers

	IER = M_INT7 ;	                             //Enable INT7 (7.1 DMA Ch1)
	EnableInterrupts();

#endif

	// Initialize DMA
	DMAInitialize();
	init_zone7();

	// Configure DMA Channel
	DMACH1AddrConfig(DMA_Dest,DMA_Source);
	DMACH1BurstConfig(31,2,2);         //Will set up to use 32-bit datasize, pointers are based on 16-bit words
	DMACH1TransferConfig(31,2,2);      //so need to increment by 2 to grab the correct location
	DMACH1WrapConfig(0xFFFF,0,0xFFFF,0);
	//Use timer0 to start the x-fer.
	//Since this is a static copy use one shot mode, so only one trigger is needed
	//Also using 32-bit mode to decrease x-fer time
	DMACH1ModeConfig(DMA_TINT0,PERINT_ENABLE,ONESHOT_ENABLE,CONT_DISABLE,SYNC_DISABLE,SYNC_SRC,OVRFLOW_DISABLE,THIRTYTWO_BIT,CHINT_END,CHINT_ENABLE);

	StartDMACH1();

	//Init the timer 0
	CpuTimer0Regs.TIM.half.LSW = 512;    //load low value so we can start the DMA quickly
	CpuTimer0Regs.TCR.bit.SOFT = 1;      //Allow to free run even if halted
	CpuTimer0Regs.TCR.bit.FREE = 1;
	CpuTimer0Regs.TCR.bit.TIE  = 1;      //Enable the timer0 interrupt signal
	CpuTimer0Regs.TCR.bit.TSS  = 0;      //restart the timer 0

}


void DMACH1_ADC_Init(volatile Uint16 *DMA_Dest,volatile Uint16 *DMA_Source)
{
	EALLOW;
	SysCtrlRegs.PCLKCR0.bit.ADCENCLK = 1;    // ADC
	EDIS;

	// Specific clock setting for this example:
	EALLOW;
	SysCtrlRegs.HISPCP.all = 3;	// HSPCLK = SYSCLKOUT/ADC_MODCLK
	EDIS;

	InitAdc();  // For this example, init the ADC

	// Specific ADC setup for this example:
	AdcRegs.ADCTRL1.bit.ACQ_PS = 0x0f;
	AdcRegs.ADCTRL3.bit.ADCCLKPS = 0x01;
	AdcRegs.ADCTRL1.bit.SEQ_CASC = 0;        // 0 Non-Cascaded Mode
	AdcRegs.ADCTRL2.bit.INT_ENA_SEQ1 = 0x1;
	AdcRegs.ADCTRL2.bit.RST_SEQ1 = 0x1;
	AdcRegs.ADCCHSELSEQ1.bit.CONV00 = 0x0;

	AdcRegs.ADCMAXCONV.bit.MAX_CONV1 = 0;   // Set up ADC to perform 4 conversions for every SOC

	// Start SEQ1
	AdcRegs.ADCTRL2.bit.SOC_SEQ1 = 0x1;

#ifdef DMA_INT_ENABLE
	// Interrupts that are used in this example are re-mapped to
	// ISR functions found within this file.
	EALLOW;	// Allow access to EALLOW protected registers
	PieVectTable.DINTCH1= &local_DINTCH1_ISR;
	EDIS;   // Disable access to EALLOW protected registers

	IER = M_INT7 ;	                             //Enable INT7 (7.1 DMA Ch1)
	EnableInterrupts();

#endif

	EALLOW;
	SysCtrlRegs.PCLKCR3.bit.DMAENCLK = 1;       // DMA Clock
	EDIS;
	// Initialize DMA
	DMAInitialize();

	// Configure DMA Channel
	DMACH1AddrConfig(DMA_Dest,DMA_Source);
	DMACH1BurstConfig(15,0,1);         //Will set up to use 32-bit datasize, pointers are based on 16-bit words
	DMACH1TransferConfig(9,0,1);      //so need to increment by 2 to grab the correct location
	DMACH1WrapConfig(40,0,40,0);
	//Use timer0 to start the x-fer.
	//Since this is a static copy use one shot mode, so only one trigger is needed
	//Also using 32-bit mode to decrease x-fer time
	DMACH1ModeConfig(DMA_SEQ1INT,PERINT_ENABLE,ONESHOT_DISABLE,CONT_DISABLE,SYNC_DISABLE,
						SYNC_SRC,OVRFLOW_DISABLE,SIXTEEN_BIT,CHINT_END,CHINT_ENABLE);

	StartDMACH1();

}



interrupt void local_DINTCH1_ISR(void)     // DMA Channel 1
{
	// To receive more interrupts from this PIE group, acknowledge this interrupt
	PieCtrlRegs.PIEACK.bit.ACK7 = 1;

//	asm ("      ESTOP0");//ok
//	for(;;);
}
