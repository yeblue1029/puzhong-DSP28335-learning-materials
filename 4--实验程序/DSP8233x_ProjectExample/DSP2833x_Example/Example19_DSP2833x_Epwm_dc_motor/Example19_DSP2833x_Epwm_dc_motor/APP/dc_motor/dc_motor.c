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

	//DC_MOTOR端口配置--1路
	GpioCtrlRegs.GPAMUX1.bit.GPIO2=0;
	GpioCtrlRegs.GPADIR.bit.GPIO2=1;

	GpioCtrlRegs.GPAMUX1.bit.GPIO3=0;
	GpioCtrlRegs.GPADIR.bit.GPIO3=1;


	//DC_MOTOR端口配置--2路
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







// 宏定义每个定时器周期寄存器的周期值；
#define EPWM2_TIMER_TBPRD  3750  // 周期值
#define EPWM2_MAX_CMPA     3700
#define EPWM2_MIN_CMPA       0
#define EPWM2_MAX_CMPB     3700
#define EPWM2_MIN_CMPB       0

/***************全局变量定义****************/
Uint16 pwm_stepValue=0;  //高电平时间
Uint16 Direction=0;//转速方向

interrupt void epwm2_isr(void);

void DCMotor_ePWM2_Init(void)
{
	EALLOW;
	SysCtrlRegs.PCLKCR0.bit.TBCLKSYNC = 1;   // Disable TBCLK within the ePWM
	SysCtrlRegs.PCLKCR1.bit.EPWM2ENCLK = 1;  // ePWM2
	EDIS;

	InitEPwm2Gpio();

	// Interrupts that are used in this example are re-mapped to
	// ISR functions found within this file.
	EALLOW;  // This is needed to write to EALLOW protected registers
	PieVectTable.EPWM2_INT = &epwm2_isr;
	EDIS;    // This is needed to disable write to EALLOW protected registers

	EALLOW;
	SysCtrlRegs.PCLKCR0.bit.TBCLKSYNC = 0;
	EDIS;

	// 设置时间基准的时钟信号（TBCLK）
	EPwm2Regs.TBCTL.bit.CTRMODE = TB_COUNT_UP; // 递增计数模式
	EPwm2Regs.TBPRD = EPWM2_TIMER_TBPRD;       // 设置定时器周期
	EPwm2Regs.TBCTL.bit.PHSEN = TB_DISABLE;    // 禁止相位加载
	EPwm2Regs.TBPHS.half.TBPHS = 0x0000;       // 时基相位寄存器的值赋值0
	EPwm2Regs.TBCTR = 0x0000;                   // 时基计数器清零
	EPwm2Regs.TBCTL.bit.HSPCLKDIV = TB_DIV2;   // 设置时基时钟速率为系统时钟SYSCLKOUT/4=37.5MHZ;
	EPwm2Regs.TBCTL.bit.CLKDIV = TB_DIV2;//由时基时钟频率和时基周期可知PWM1频率=10KHZ；

	// 设置比较寄存器的阴影寄存器加载条件：时基计数到0
	EPwm2Regs.CMPCTL.bit.SHDWAMODE = CC_SHADOW;
	EPwm2Regs.CMPCTL.bit.SHDWBMODE = CC_SHADOW;
	EPwm2Regs.CMPCTL.bit.LOADAMODE = CC_CTR_ZERO;
	EPwm2Regs.CMPCTL.bit.LOADBMODE = CC_CTR_ZERO;


	// 设置比较寄存器的值
	EPwm2Regs.CMPA.half.CMPA = EPWM2_MIN_CMPA;     // 设置比较寄存器A的值
	EPwm2Regs.CMPB = EPWM2_MIN_CMPB;               // 设置比较寄存器B的值

	// 设置动作限定；首先默认为转动方向为正转，这时只有PWM1A输出占空比；
	EPwm2Regs.AQCTLA.bit.ZRO = AQ_SET;            // 计数到0时PWM1A输出高电平
	EPwm2Regs.AQCTLA.bit.CAU = AQ_CLEAR;          // 递增计数时，发生比较寄存器A匹配时清除PWM1A输出

	EPwm2Regs.AQCTLB.bit.ZRO = AQ_CLEAR;            // 计数到0时PWM1B输出低电平
	EPwm2Regs.AQCTLB.bit.CBU = AQ_CLEAR;          // 递增计数时，发生比较寄存器A匹配时清除PWM1B输出

	// 3次0匹配事件发生时产生一个中断请求；一次匹配是100us，一共300us产生一次中断；
	EPwm2Regs.ETSEL.bit.INTSEL = ET_CTR_ZERO;     // 选择0匹配事件中断
	EPwm2Regs.ETSEL.bit.INTEN = 1;                // 使能事件触发中断
	EPwm2Regs.ETPS.bit.INTPRD = ET_3RD;           // 3次事件产生中断请求

	EALLOW;
	SysCtrlRegs.PCLKCR0.bit.TBCLKSYNC = 1;
	EDIS;

	IER |= M_INT3;
	PieCtrlRegs.PIEIER3.bit.INTx2 = 1;

	EINT;   // Enable Global interrupt INTM
	ERTM;   // Enable Global realtime interrupt DBGM
}

interrupt void epwm2_isr(void)
{
	static unsigned char key=0;

	key=KEY_Scan(0);
	if(key==KEY1_PRESS||key==KEY2_PRESS||key==KEY3_PRESS)
	{
		if(key==KEY3_PRESS)
		{
			//保证下面EPWMA和EPWMB相互切换同时输出0电平；
			EPwm2Regs.CMPA.half.CMPA = 0;//改变脉宽
			EPwm2Regs.CMPB = 0;//改变脉宽

			if(Direction==0)
			{
				// 设置动作限定；首先默认为转动方向为反转，这时只有PWM1B输出占空比；
				EPwm2Regs.AQCTLA.bit.ZRO = AQ_CLEAR;            // 计数到0时PWM1A输出低电平
				EPwm2Regs.AQCTLA.bit.CAU = AQ_CLEAR;          // 递增计数时，发生比较寄存器A匹配时清除PWM1A输出

				EPwm2Regs.AQCTLB.bit.ZRO = AQ_SET;            // 计数到0时PWM1B输出高电平
				EPwm2Regs.AQCTLB.bit.CBU = AQ_CLEAR;          // 递增计数时，发生比较寄存器A匹配时清除PWM1B输出
				Direction=1;
			}
			else
			{
				// 设置动作限定；首先默认为转动方向为正转，这时只有PWM1A输出占空比；
				EPwm2Regs.AQCTLA.bit.ZRO = AQ_SET;            // 计数到0时PWM1A输出高电平
				EPwm2Regs.AQCTLA.bit.CAU = AQ_CLEAR;          // 递增计数时，发生比较寄存器A匹配时清除PWM1A输出

				EPwm2Regs.AQCTLB.bit.ZRO = AQ_CLEAR;            // 计数到0时PWM1B输出低电平
				EPwm2Regs.AQCTLB.bit.CBU = AQ_CLEAR;          // 递增计数时，发生比较寄存器A匹配时清除PWM1B输出
				Direction=0;
			}
			pwm_stepValue=0;
		}
		else
		{
			if(key==KEY1_PRESS)
			{
				if(pwm_stepValue!=3500)
					pwm_stepValue+=500;
			}
			else if(key==KEY2_PRESS)
			{
				if(pwm_stepValue!=0)
					pwm_stepValue=pwm_stepValue-500;
			}
		}

		EPwm2Regs.CMPA.half.CMPA = pwm_stepValue;//改变脉宽
		EPwm2Regs.CMPB = pwm_stepValue;//改变脉宽
	}

	// 清除这个定时器的中断标志位
	EPwm2Regs.ETCLR.bit.INT = 1;
	// 清除PIE应答寄存器的第三位，以响应组3内的其他中断请求；
	PieCtrlRegs.PIEACK.all = PIEACK_GROUP3;
}

