/*
 * spi.c
 *
 *  Created on: 2018-2-3
 *      Author: Administrator
 */


#include "spi.h"


void SPIA_Init(void)
{
	EALLOW;
	SysCtrlRegs.PCLKCR0.bit.SPIAENCLK = 1;   // SPI-A
	EDIS;

	InitSpiaGpio();

	// Initialize SPI FIFO registers
	SpiaRegs.SPIFFTX.all=0xE040;
	SpiaRegs.SPIFFRX.all=0x204f;
	SpiaRegs.SPIFFCT.all=0x0;


	SpiaRegs.SPICCR.all =0x000F;	             // Reset on, rising edge, 16-bit char bits
	SpiaRegs.SPICTL.all =0x0006;    		     // Enable master mode, normal phase,
	                                                 // enable talk, and SPI int disabled.
	SpiaRegs.SPIBRR =0x007F;
	SpiaRegs.SPICCR.all =0x00DF;		         // Relinquish SPI from Reset
	SpiaRegs.SPIPRI.bit.FREE = 1;                // Set so breakpoints don't disturb xmission

}

Uint16 SPIA_SendReciveData(Uint16 dat)
{
	// Transmit data
	SpiaRegs.SPITXBUF=dat;

	// Wait until data is received
	while(SpiaRegs.SPIFFRX.bit.RXFFST !=1);

	return SpiaRegs.SPIRXBUF;
}


#ifdef SPIA_TXRX_INT_FIFO

Uint16 sdata[8];     // Send data buffer
Uint16 rdata[8];     // Receive data buffer
Uint16 errcounter;
Uint16 rdata_point;  // Keep track of where we are
                     // in the data stream to check received data
void spi_error(void)
{
    errcounter++;
    asm("     ESTOP0");	 //Test failed!! Stop!
    for (;;);
}

interrupt void spiTxFifoIsr(void)
{
 	Uint16 i;
    for(i=0;i<8;i++)
    {
 	   SpiaRegs.SPITXBUF=sdata[i];      // Send data
    }

    for(i=0;i<8;i++)                    // Increment data for next cycle
    {
 	   sdata[i]++;
    }


    SpiaRegs.SPIFFTX.bit.TXFFINTCLR=1;  // Clear Interrupt flag
	PieCtrlRegs.PIEACK.all|=0x20;  		// Issue PIE ACK
}

interrupt void spiRxFifoIsr(void)
{
    Uint16 i;
    for(i=0;i<8;i++)
    {
	    rdata[i]=SpiaRegs.SPIRXBUF;		// Read data
	}
	for(i=0;i<8;i++)                    // Check received data
	{
	    if(rdata[i] != rdata_point+i) spi_error(); //运行一段时间后，在此处设置断点
	}
	rdata_point++;
	SpiaRegs.SPIFFRX.bit.RXFFOVFCLR=1;  // Clear Overflow flag
	SpiaRegs.SPIFFRX.bit.RXFFINTCLR=1; 	// Clear Interrupt flag
	PieCtrlRegs.PIEACK.all|=0x20;       // Issue PIE ack
}

void SPIA_INT_Init(void)
{
	EALLOW;
	SysCtrlRegs.PCLKCR0.bit.SPIAENCLK = 1;   // SPI-A
	EDIS;

	InitSpiaGpio();

	// Interrupts that are used in this example are re-mapped to
	// ISR functions found within this file.
	EALLOW;	// This is needed to write to EALLOW protected registers
	PieVectTable.SPIRXINTA = &spiRxFifoIsr;
	PieVectTable.SPITXINTA = &spiTxFifoIsr;
	EDIS;   // This is needed to disable write to EALLOW protected registers


	// Initialize SPI FIFO registers
	SpiaRegs.SPICCR.bit.SPISWRESET=0; // Reset SPI

	SpiaRegs.SPICCR.all=0x001F;       //16-bit character, Loopback mode
	SpiaRegs.SPICTL.all=0x0017;       //Interrupt enabled, Master/Slave XMIT enabled
	SpiaRegs.SPISTS.all=0x0000;
	SpiaRegs.SPIBRR=0x0063;           // Baud rate
	SpiaRegs.SPIFFTX.all=0xC028;      // Enable FIFO's, set TX FIFO level to 8
	SpiaRegs.SPIFFRX.all=0x0028;      // Set RX FIFO level to 8
	SpiaRegs.SPIFFCT.all=0x00;
	SpiaRegs.SPIPRI.all=0x0010;

	SpiaRegs.SPICCR.bit.SPISWRESET=1;  // Enable SPI

	SpiaRegs.SPIFFTX.bit.TXFIFO=1;
	SpiaRegs.SPIFFRX.bit.RXFIFORESET=1;

	// Enable interrupts required for this example
	PieCtrlRegs.PIECTRL.bit.ENPIE = 1;   // Enable the PIE block
	PieCtrlRegs.PIEIER6.bit.INTx1=1;     // Enable PIE Group 6, INT 1
	PieCtrlRegs.PIEIER6.bit.INTx2=1;     // Enable PIE Group 6, INT 2
	IER=0x20;                            // Enable CPU INT6
	EINT;                                // Enable Global Interrupts

}

void SPIA_INTFIFO_Test(void)
{
	unsigned char i=0;

	for(i=0; i<8; i++)
	{
		sdata[i] = i;
	}
	rdata_point = 0;

	SPIA_INT_Init();

}

#endif
