/*
 * relay.c
 *
 *  Created on: 2018-1-22
 *      Author: Administrator
 */

#include "relay.h"
#include "key.h"

void Relay_Init(void)
{
	EALLOW;
	SysCtrlRegs.PCLKCR3.bit.GPIOINENCLK = 1;// 开启GPIO时钟

	//继电器端口配置
	GpioCtrlRegs.GPAMUX1.bit.GPIO15=0;
	GpioCtrlRegs.GPADIR.bit.GPIO15=1;
	GpioCtrlRegs.GPAPUD.bit.GPIO15=0;

	EDIS;

	GpioDataRegs.GPACLEAR.bit.GPIO15=1;
}

extern char KEYValue;

void RELAY_Test(void)
{

	Relay_Init();

	RELAY_ON;
	while(1)
	{

		if(KEYValue!=KEY3_PRESS)
		{
			RELAY_OFF;
			return;
		}
	}
}
