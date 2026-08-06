/*
 * step_motor.c
 *
 *  Created on: 2018-1-23
 *      Author: Administrator
 */

#include "step_motor.h"
#include "key.h"


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

#ifdef STEP_MOTOR_5LINE4
unsigned char Step_table_ZTurn[]={0xfff7,0xfffb,0xffdf,0xffef};
unsigned char Step_table_FTurn[]={0xffef,0xffdf,0xfffb,0xfff7};
#endif

#ifdef STEP_MOTOR_4LINE2
unsigned char Step_table_ZTurn[]={0xfff7,0xffdf,0xfffb,0xffef};
unsigned char Step_table_FTurn[]={0xffef,0xfffb,0xffdf,0xfff7};
#endif


extern char KEYValue;

void STEPMotor_Test(void)
{
	char j=0;

	Step_Motor_Init();

	while(1)
	{
#ifdef STEP_MOTOR_4LINE2
		for(j=0;j<4;j++)
		{
			GpioDataRegs.GPADAT.all=Step_table_ZTurn[j];
			DELAY_US(5000);
		}
#endif

#ifdef STEP_MOTOR_5LINE4
		for(j=0;j<4;j++)
		{
			GpioDataRegs.GPADAT.all=Step_table_ZTurn[j];
			DELAY_US(5000);
		}
#endif
		if(KEYValue!=KEY5_PRESS)
		{

			return;
		}
	}
}

