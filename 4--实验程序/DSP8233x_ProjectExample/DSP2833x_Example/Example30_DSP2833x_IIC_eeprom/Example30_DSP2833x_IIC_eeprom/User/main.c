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
#include "stdio.h"
#include "24cxx.h"
#include "key.h"
#include "smg.h"


/*******************************************************************************
* 函 数 名         : main
* 函数功能		   : 主函数
* 输    入         : 无
* 输    出         : 无
*******************************************************************************/
void main()
{
	int i=0;
	unsigned char key=0,k=0;


	InitSysCtrl();
	InitPieCtrl();
	IER = 0x0000;
	IFR = 0x0000;
	InitPieVectTable();

	LED_Init();
	TIM0_Init(150,200000);//200ms
	UARTa_Init(4800);
	SMG_Init();
	KEY_Init();
	AT24CXX_Init();

	while(AT24CXX_Check())  //检测AT24C02是否正常
	{
		UARTa_SendString("AT24C02检测不正常!\r\n");
		DELAY_US(500*1000);
	}
	UARTa_SendString("AT24C02检测正常!\r\n");


	while(1)
	{
		key=KEY_Scan(0);
		if(key==KEY1_PRESS)
		{
			k++;
			if(k>255)
			{
				k=255;
			}
			AT24CXX_WriteOneByte(0,k);

		}
		else if(key==KEY2_PRESS)
		{
			k=AT24CXX_ReadOneByte(0);
		}
		else if(key==KEY3_PRESS)
		{
			k=0;
		}

		SMG_DisplayInt(k);
	}
}

