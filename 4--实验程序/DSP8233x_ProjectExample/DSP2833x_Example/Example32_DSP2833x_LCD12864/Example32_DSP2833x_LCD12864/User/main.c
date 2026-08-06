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
#include "lcd12864.h"



/*******************************************************************************
* 函 数 名         : main
* 函数功能		   : 主函数
* 输    入         : 无
* 输    出         : 无
*******************************************************************************/
void main()
{
	unsigned char i=0;


	InitSysCtrl();
	InitPieCtrl();
	IER = 0x0000;
	IFR = 0x0000;
	InitPieVectTable();


	LED_Init();
	TIM0_Init(150,200000);//200ms
	UARTa_Init(4800);
	LCD12864_Init();
	LCD12864_ClearScreen();
	LCD12864_DisplayPic();
	DELAY_US(1000000);
	while(1)
	{
		for (i=0; i<8; i += 2)
		{
			LCD12864_ClearScreen();
			//--由于这个函数显示方向正好相反--//
			LCD12864_Write16CnCHAR(0, i, "普中科技有限公司");
			DELAY_US(500000);
		}
	}
}


