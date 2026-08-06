/*
 * led.c
 *
 *  Created on: 2018-1-20
 *      Author: Administrator
 */
#include "leds.h"
#include "key.h"

/*******************************************************************************
* 函 数 名         : LED_Init
* 函数功能		   : LED初始化函数
* 输    入         : 无
* 输    出         : 无
*******************************************************************************/
void LED_Init(void)
{
	EALLOW;
	SysCtrlRegs.PCLKCR3.bit.GPIOINENCLK = 1;// 开启GPIO时钟

	//LED1端口配置
	GpioCtrlRegs.GPCMUX1.bit.GPIO68=0;
	GpioCtrlRegs.GPCDIR.bit.GPIO68=1;
	GpioCtrlRegs.GPCPUD.bit.GPIO68=0;

	//LED2端口配置
	GpioCtrlRegs.GPCMUX1.bit.GPIO67=0;
	GpioCtrlRegs.GPCDIR.bit.GPIO67=1;
	GpioCtrlRegs.GPCPUD.bit.GPIO67=0;

	//LED3端口配置
	GpioCtrlRegs.GPCMUX1.bit.GPIO66=0;
	GpioCtrlRegs.GPCDIR.bit.GPIO66=1;
	GpioCtrlRegs.GPCPUD.bit.GPIO66=0;

	//LED4端口配置
	GpioCtrlRegs.GPCMUX1.bit.GPIO65=0;
	GpioCtrlRegs.GPCDIR.bit.GPIO65=1;
	GpioCtrlRegs.GPCPUD.bit.GPIO65=0;

	//LED5端口配置
	GpioCtrlRegs.GPCMUX1.bit.GPIO64=0;
	GpioCtrlRegs.GPCDIR.bit.GPIO64=1;
	GpioCtrlRegs.GPCPUD.bit.GPIO64=0;

	//LED6端口配置
	GpioCtrlRegs.GPAMUX1.bit.GPIO10=0;
	GpioCtrlRegs.GPADIR.bit.GPIO10=1;
	GpioCtrlRegs.GPAPUD.bit.GPIO10=0;

	//LED7端口配置
	GpioCtrlRegs.GPAMUX1.bit.GPIO11=0;
	GpioCtrlRegs.GPADIR.bit.GPIO11=1;
	GpioCtrlRegs.GPAPUD.bit.GPIO11=0;



	GpioDataRegs.GPCSET.bit.GPIO68=1;
	GpioDataRegs.GPCSET.bit.GPIO67=1;
	GpioDataRegs.GPCSET.bit.GPIO66=1;
	GpioDataRegs.GPCSET.bit.GPIO65=1;
	GpioDataRegs.GPCSET.bit.GPIO64=1;
	GpioDataRegs.GPASET.bit.GPIO10=1;
	GpioDataRegs.GPASET.bit.GPIO11=1;

	EDIS;
}


extern char KEYValue;
char LED_Flag=0;
void LED_Test(void)
{
	LED_Flag=1;
	while(1)
	{
		LED1_ON;LED2_OFF;LED3_OFF;LED4_OFF;LED5_OFF;LED6_OFF;LED7_OFF;
		DELAY_US(200000);
		LED1_OFF;LED2_ON;LED3_OFF;LED4_OFF;LED5_OFF;LED6_OFF;LED7_OFF;
		DELAY_US(200000);
		LED1_OFF;LED2_OFF;LED3_ON;LED4_OFF;LED5_OFF;LED6_OFF;LED7_OFF;
		DELAY_US(200000);
		LED1_OFF;LED2_OFF;LED3_OFF;LED4_ON;LED5_OFF;LED6_OFF;LED7_OFF;
		DELAY_US(200000);
		LED1_OFF;LED2_OFF;LED3_OFF;LED4_OFF;LED5_ON;LED6_OFF;LED7_OFF;
		DELAY_US(200000);
		LED1_OFF;LED2_OFF;LED3_OFF;LED4_OFF;LED5_OFF;LED6_ON;LED7_OFF;
		DELAY_US(200000);
		LED1_OFF;LED2_OFF;LED3_OFF;LED4_OFF;LED5_OFF;LED6_OFF;LED7_ON;
		DELAY_US(200000);

		if(KEYValue!=KEY1_PRESS)
		{
			LED1_OFF;LED2_OFF;LED3_OFF;LED4_OFF;LED5_OFF;LED6_OFF;LED7_OFF;
			return;
		}
	}
}
