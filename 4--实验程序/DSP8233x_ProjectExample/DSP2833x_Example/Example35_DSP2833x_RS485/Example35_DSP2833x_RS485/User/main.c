/*
 * main.c
 *
 *  Created on: 2018-3-21
 *      Author: Administrator
 */


#include "DSP2833x_Device.h"     // DSP2833x Headerfile Include File
#include "DSP2833x_Examples.h"   // DSP2833x Examples Include File

#include "leds.h"
#include "time.h"
#include "uart.h"
#include "rs485.h"



/*******************************************************************************
* 函 数 名         : main
* 函数功能		   : 主函数
* 输    入         : 无
* 输    出         : 无
*******************************************************************************/
void main()
{
	Uint16 ReceivedChar;
	char *msg;

	InitSysCtrl();
	InitPieCtrl();
	IER = 0x0000;
	IFR = 0x0000;
	InitPieVectTable();

	LED_Init();
	TIM0_Init(150,200000);//200ms
	RS485_Init(4800);
	RS485_DIR_SETH;
	DELAY_US(5);
	msg =  "\r\n*******welcome to prechin**********\0";
	RS485_SendString(msg);

	while(1)
	{
		msg = "\r\nEnter a character: \0";
		RS485_SendString(msg);
		DELAY_US(2);
		RS485_DIR_SETL;
		ScibRegs.SCICTL1.bit.SWRESET=0;
		DELAY_US(2);
		ScibRegs.SCICTL1.bit.SWRESET=1;
		// Wait for inc character
		while(ScibRegs.SCIRXST.bit.RXRDY !=1); // wait for XRDY =1 for empty state
		// Get character
		ReceivedChar = ScibRegs.SCIRXBUF.all;
		RS485_DIR_SETH;
		DELAY_US(5);
		// Echo character back
		msg = "you enter is:\0";
		RS485_SendString(msg);
		RS485_SendByte(ReceivedChar);
	}
}

