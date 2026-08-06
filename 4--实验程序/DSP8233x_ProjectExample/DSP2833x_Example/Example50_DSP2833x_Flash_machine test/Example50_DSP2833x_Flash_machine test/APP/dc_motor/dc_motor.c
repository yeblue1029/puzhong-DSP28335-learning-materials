/*
 * dc_motor.c
 *
 *  Created on: 2018-1-23
 *      Author: Administrator
 */


#include "dc_motor.h"
#include "key.h"


void DC_Motor_Init(void)
{
	EALLOW;
	SysCtrlRegs.PCLKCR3.bit.GPIOINENCLK = 1;// 开启GPIO时钟
	//DC_MOTOR 第1路端口配置
	GpioCtrlRegs.GPAMUX1.bit.GPIO2=0;
	GpioCtrlRegs.GPADIR.bit.GPIO2=1;

	GpioCtrlRegs.GPAMUX1.bit.GPIO3=0;
	GpioCtrlRegs.GPADIR.bit.GPIO3=1;

	//DC_MOTOR 第2路端口配置
	GpioCtrlRegs.GPAMUX1.bit.GPIO4=0;
	GpioCtrlRegs.GPADIR.bit.GPIO4=1;

	GpioCtrlRegs.GPAMUX1.bit.GPIO5=0;
	GpioCtrlRegs.GPADIR.bit.GPIO5=1;

	EDIS;

	GpioDataRegs.GPACLEAR.bit.GPIO2=1;
	GpioDataRegs.GPACLEAR.bit.GPIO3=1;
	GpioDataRegs.GPACLEAR.bit.GPIO4=1;
	GpioDataRegs.GPACLEAR.bit.GPIO5=1;
}



extern char KEYValue;

void DCMotor_Test(void)
{

	DC_Motor_Init();

	while(1)
	{
		DC_MOTOR_INA_SETH;
		DC_MOTOR_INB_SETL;

		if(KEYValue!=KEY4_PRESS)
		{
			DC_MOTOR_INA_SETL;
			DC_MOTOR_INB_SETL;
			return;
		}
	}
}
