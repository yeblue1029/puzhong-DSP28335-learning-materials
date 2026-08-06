/*
 * main.c
 *
 *  Created on: 2018-3-21
 *      Author: Administrator
 */


#include "DSP2833x_Device.h"     // DSP2833x Headerfile Include File
#include "DSP2833x_Examples.h"   // DSP2833x Examples Include File

#include "leds.h"
#include "beep.h"

/*******************************************************************************
* 函 数 名         : main
* 函数功能		   : 主函数
* 输    入         : 无
* 输    出         : 无
*******************************************************************************/
void main()
{
	int i=0;

	InitSysCtrl();

	LED_Init();
	BEEP_Init();

	while(1)
	{
		i++;

		BEEP_TOGGLE;

		if(i%1000==0)
		{
			LED1_TOGGLE;
		}
		DELAY_US(100);
	}
}

