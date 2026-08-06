/*
 * step_motor.c
 *
 *  Created on: 2018-1-23
 *      Author: Administrator
 */

#include "step_motor.h"



void Step_Motor_Init(void)
{
	EALLOW;
	SysCtrlRegs.PCLKCR3.bit.GPIOINENCLK = 1;// ø™∆ÙGPIO ±÷”
	//Step_MOTOR∂Àø⁄≈‰÷√
	GpioCtrlRegs.GPAMUX1.bit.GPIO2=0;
	GpioCtrlRegs.GPADIR.bit.GPIO2=1;

	GpioCtrlRegs.GPAMUX1.bit.GPIO3=0;
	GpioCtrlRegs.GPADIR.bit.GPIO3=1;

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


