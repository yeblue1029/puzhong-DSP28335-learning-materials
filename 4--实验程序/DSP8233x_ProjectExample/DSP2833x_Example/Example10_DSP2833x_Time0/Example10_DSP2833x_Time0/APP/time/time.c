/*
 * time.c
 *
 *  Created on: 2018-1-24
 *      Author: Administrator
 */


#include "time.h"
#include "leds.h"


//定时器0初始化函数
//Freq：CPU时钟频率（150MHz）
//Period：定时周期值，单位us
void TIM0_Init(float Freq, float Period)
{
	EALLOW;
	SysCtrlRegs.PCLKCR3.bit.CPUTIMER0ENCLK = 1; // CPU Timer 0
	EDIS;

	//设置定时器0的中断入口地址为中断向量表的INT0
	EALLOW;
	PieVectTable.TINT0 = &TIM0_IRQn;
	EDIS;

	//指向定时器0的寄存器地址
	CpuTimer0.RegsAddr = &CpuTimer0Regs;
	//设置定时器0的周期寄存器值
	CpuTimer0Regs.PRD.all  = 0xFFFFFFFF;
	//设置定时器预定标计数器值为0
	CpuTimer0Regs.TPR.all  = 0;
	CpuTimer0Regs.TPRH.all = 0;
	//确保定时器0为停止状态
	CpuTimer0Regs.TCR.bit.TSS = 1;
	//重载使能
	CpuTimer0Regs.TCR.bit.TRB = 1;
	// Reset interrupt counters:
	CpuTimer0.InterruptCount = 0;

	ConfigCpuTimer(&CpuTimer0, Freq, Period);

	//开始定时器功能
	CpuTimer0Regs.TCR.bit.TSS=0;
	//开启CPU第一组中断并使能第一组中断的第7个小中断，即定时器0
	IER |= M_INT1;
	PieCtrlRegs.PIEIER1.bit.INTx7 = 1;
	//使能总中断
	EINT;
	ERTM;

}

interrupt void TIM0_IRQn(void)
{
	EALLOW;
	LED2_TOGGLE;
	PieCtrlRegs.PIEACK.bit.ACK1=1;
	EDIS;
}


