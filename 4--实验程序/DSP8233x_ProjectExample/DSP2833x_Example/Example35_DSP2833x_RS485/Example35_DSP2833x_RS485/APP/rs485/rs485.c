/*
 * rs485.c
 *
 *  Created on: 2018-4-21
 *      Author: Administrator
 */


#include "rs485.h"


void RS485_Init(Uint32 baud)
{
	unsigned char scihbaud=0;
	unsigned char scilbaud=0;
	Uint16 scibaud=0;

	scibaud=37500000/(8*baud)-1;
	scihbaud=scibaud>>8;
	scilbaud=scibaud&0xff;


	EALLOW;
	SysCtrlRegs.PCLKCR0.bit.SCIBENCLK = 1;   // SCI-B
	EDIS;

	InitSciGpio();

	EALLOW;
	//RS485_EN∂Àø⁄≈‰÷√
	GpioCtrlRegs.GPBMUX2.bit.GPIO61=0;
	GpioCtrlRegs.GPBDIR.bit.GPIO61=1;
	GpioCtrlRegs.GPBPUD.bit.GPIO61=0;
	GpioDataRegs.GPBSET.bit.GPIO61=1;
	EDIS;

	// Note: Clocks were turned on to the SCIA peripheral
	// in the InitSysCtrl() function
	ScibRegs.SCICCR.all =0x0007;   // 1 stop bit,  No loopback
								   // No parity,8 char bits,
								   // async mode, idle-line protocol
	ScibRegs.SCICTL1.all =0x0003;  // enable TX, RX, internal SCICLK,
								   // Disable RX ERR, SLEEP, TXWAKE
	ScibRegs.SCICTL2.all =0x0003;
	ScibRegs.SCICTL2.bit.TXINTENA =1;
	ScibRegs.SCICTL2.bit.RXBKINTENA =1;
	ScibRegs.SCIHBAUD    =scihbaud;  // 9600 baud @LSPCLK = 37.5MHz.
	ScibRegs.SCILBAUD    =scilbaud;
	ScibRegs.SCICTL1.all =0x0023;     // Relinquish SCI from Reset

}

// Transmit a character from the SCI'
void RS485_SendByte(int a)
{
	while (ScibRegs.SCICTL2.bit.TXEMPTY == 0);
	ScibRegs.SCITXBUF=a;
}

void RS485_SendString(char * msg)
{
	int i=0;

	while(msg[i] != '\0')
	{
		RS485_SendByte(msg[i]);
		i++;
	}
}


