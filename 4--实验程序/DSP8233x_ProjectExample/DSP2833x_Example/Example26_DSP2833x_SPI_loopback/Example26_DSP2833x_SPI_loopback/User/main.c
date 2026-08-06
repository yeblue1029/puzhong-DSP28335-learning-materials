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
#include "spi.h"
#include "stdio.h"


/*******************************************************************************
* 函 数 名         : main
* 函数功能		   : 主函数
* 输    入         : 无
* 输    出         : 无
*******************************************************************************/
void main()
{
	int i=0;
	Uint16 senddata=0;
	Uint16 recdata=0;
	char str[40];

	InitSysCtrl();
	InitPieCtrl();
	IER = 0x0000;
	IFR = 0x0000;
	InitPieVectTable();

	LED_Init();
	TIM0_Init(150,200000);//200ms
	UARTa_Init(4800);
	SPIA_Init();

	while(1)
	{
		i++;
		if(i%500==0)
		{
			recdata=SPIA_SendReciveData(senddata++);
			sprintf(str,"senddata=%d    recdata=%d\r\n",senddata,recdata);
			UARTa_SendString(str);
		}
		DELAY_US(1000);
	}
}

