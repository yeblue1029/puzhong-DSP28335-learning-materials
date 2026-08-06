/*
 * main.c
 *
 *  Created on: 2018-3-21
 *      Author: Administrator
 */


#include "DSP2833x_Device.h"     // DSP2833x Headerfile Include File
#include "DSP2833x_Examples.h"   // DSP2833x Examples Include File

#include "leds.h"
#include "key.h"
#include "step_motor.h"


#ifdef STEP_MOTOR_5LINE4
unsigned char Step_table_ZTurn[]={0xfff7,0xfffb,0xffdf,0xffef};
unsigned char Step_table_FTurn[]={0xffef,0xffdf,0xfffb,0xfff7};
#endif

#ifdef STEP_MOTOR_4LINE2
unsigned char Step_table_ZTurn[]={0xfff7,0xffdf,0xfffb,0xffef};
unsigned char Step_table_FTurn[]={0xffef,0xfffb,0xffdf,0xfff7};
#endif


/*******************************************************************************
* 函 数 名         : main
* 函数功能		   : 主函数
* 输    入         : 无
* 输    出         : 无
*******************************************************************************/
void main()
{
	int i=0;
	char key=0;
	short cnt=0;
	char j=0;

	InitSysCtrl();

	LED_Init();
	KEY_Init();
	Step_Motor_Init();

	while(1)
	{
		key=KEY_Scan(0);

#ifdef STEP_MOTOR_4LINE2
		if(key==KEY1_PRESS)
		{
			cnt=1024;
			while(cnt--)
			{
				for(j=0;j<4;j++)
				{
					GpioDataRegs.GPADAT.all=Step_table_ZTurn[j];
					DELAY_US(5000);
				}
			}
		}
		else if(key==KEY2_PRESS)
		{
			cnt=1024;
			while(cnt--)
			{
				for(j=0;j<4;j++)
				{
					GpioDataRegs.GPADAT.all=Step_table_FTurn[j];
					DELAY_US(5000);
				}
			}
		}
#endif

#ifdef STEP_MOTOR_5LINE4
		if(key==KEY1_PRESS)
		{
			cnt=1024;
			while(cnt--)
			{
				for(j=0;j<4;j++)
				{
					GpioDataRegs.GPADAT.all=Step_table_ZTurn[j];
					DELAY_US(5000);
				}
			}
		}
		else if(key==KEY2_PRESS)
		{
			cnt=1024;
			while(cnt--)
			{
				for(j=0;j<4;j++)
				{
					GpioDataRegs.GPADAT.all=Step_table_FTurn[j];
					DELAY_US(5000);
				}
			}
		}
#endif

		i++;
		if(i%2000==0)
		{
			LED1_TOGGLE;
		}
		DELAY_US(100);
	}
}

