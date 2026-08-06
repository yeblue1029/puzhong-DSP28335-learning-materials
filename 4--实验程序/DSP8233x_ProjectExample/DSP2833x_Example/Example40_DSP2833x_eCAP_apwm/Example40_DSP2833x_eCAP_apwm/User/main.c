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
#include "ecap.h"



// Global variables
Uint16 direction = 0;

/*******************************************************************************
* 函 数 名         : main
* 函数功能		   : 主函数
* 输    入         : 无
* 输    出         : 无
*******************************************************************************/
void main()
{
	Uint16 i=0;


	InitSysCtrl();
	InitPieCtrl();
	IER = 0x0000;
	IFR = 0x0000;
	InitPieVectTable();

	LED_Init();
	TIM0_Init(150,200000);//200ms
	UARTa_Init(4800);

	eCAP1_APWM_Init();

	while(1)
	{
		// set next duty cycle to 50%
		ECap1Regs.CAP4 = ECap1Regs.CAP1 >> 1;

		// vary freq between 7.5 Hz and 15 Hz (for 150MHz SYSCLKOUT) 5 Hz and 10 Hz (for 100 MHz SYSCLKOUT)
		if(ECap1Regs.CAP1 >= 0x01312D00)
		{
			direction = 0;
		}
		else if (ECap1Regs.CAP1 <= 0x00989680)
		{
			direction = 1;
		}

		if(direction == 0)
		{
			ECap1Regs.CAP3 = ECap1Regs.CAP1 - 500000;
		}
		else
		{
			ECap1Regs.CAP3 = ECap1Regs.CAP1 + 500000;
		}
	}
}

