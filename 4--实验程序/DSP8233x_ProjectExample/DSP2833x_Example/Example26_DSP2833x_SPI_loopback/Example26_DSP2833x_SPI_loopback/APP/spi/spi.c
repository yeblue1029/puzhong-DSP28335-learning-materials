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
	SpiaRegs.SPICCR.all =0x009F;		         // Relinquish SPI from Reset
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
