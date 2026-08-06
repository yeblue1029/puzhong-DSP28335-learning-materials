/*
 * tlv5620.c
 *
 *  Created on: 2018-3-1
 *      Author: Administrator
 */

#include "tlv5620.h"


void TLV5620_Init(void)
{
	EALLOW;
	SysCtrlRegs.PCLKCR0.bit.SPIAENCLK = 1;   // SPI-A
	EDIS;

	/*初始化GPIO;*/
	InitSpiaGpio();

	EALLOW;
	GpioCtrlRegs.GPAMUX2.bit.GPIO26 = 0; // 配置GPIO为GPIO口
	GpioCtrlRegs.GPADIR.bit.GPIO26 = 1;      // 定义GPIO输出引脚
	GpioCtrlRegs.GPAPUD.bit.GPIO26 = 0;      // 禁止上啦 GPIO引脚
	EDIS;

	SpiaRegs.SPICCR.all =0x0a;///进入初始状态，数据在上升沿输出，自测禁止，11位数据模式
	SpiaRegs.SPICTL.all =0x0006; // 使能主机模式，正常相位，使能主机发送，禁止接收
		                            //溢出中断，禁止SPI中断；
	SpiaRegs.SPIBRR =0x0031;	//SPI波特率=37.5M/50	=0.75MHZ；
	SpiaRegs.SPICCR.all =0x8a; //退出初始状态；
	SpiaRegs.SPIPRI.bit.FREE = 1;  // 自由运行

	SET_LOAD;
}


///大家要知道这里所定义的各个变量的含义,add是4个通道的地址（00，01，10，11）
///                                     RNG是输出范围的倍数，可以是0或1。
///                                     VOL是0~256数据
void DAC_SetChannelData(unsigned char channel,unsigned char rng,unsigned char dat)
{
	Uint16 dacvalue=0;

	//注意这里的有效数据是11位，SPI初始化中也进行了定义
	dacvalue = ((channel<<14) | (rng<<13) | (dat<<5));

	while(SpiaRegs.SPISTS.bit.BUFFULL_FLAG ==1);//判断SPI的发送缓冲区是否是空的,等于0可写数据
	SpiaRegs.SPITXBUF = dacvalue;	//把发送的数据写如SPI发送缓冲区
	while( SpiaRegs.SPISTS.bit.BUFFULL_FLAG==1);		//当发送缓冲区出现满标志位时,开始琐存数据

	ClEAR_LOAD;
	DELAY_US(2);

	SET_LOAD;
	DELAY_US(10);

}


