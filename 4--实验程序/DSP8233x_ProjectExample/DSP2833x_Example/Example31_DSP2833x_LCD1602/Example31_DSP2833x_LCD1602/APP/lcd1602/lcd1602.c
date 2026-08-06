/*
 * lcd1602.c
 *
 *  Created on: 2018-2-28
 *      Author: Administrator
 */

#include "lcd1602.h"


void LCD1602_GPIOInit(void)
{
	EALLOW;
	SysCtrlRegs.PCLKCR3.bit.GPIOINENCLK = 1;// 开启GPIO时钟
	GpioCtrlRegs.GPAPUD.bit.GPIO0 = 0;    // 使能GPIO0 引脚内部上拉
	GpioCtrlRegs.GPAPUD.bit.GPIO1 = 0;   // 禁止GPIO1 引脚内部上拉
	GpioCtrlRegs.GPAMUX1.all = 0;   // 配置GPIO0-GPIO15为通用I/O口
	GpioCtrlRegs.GPADIR.all = 0x00FFF;// 配置GPIO0-GPIO11为输出引脚

	// 每个输入口可以有不同的输入限定
	// a) 输入与系统时钟 SYSCLKOUT同步
	// b) 输入被指定的采样窗口限定
	// c) 输入异步 (仅对外设输入有效)
	GpioCtrlRegs.GPAQSEL1.all = 0x0000;    // GPIO0-GPIO15与系统时钟SYSCLKOUT 同步
	//输出数据LCD_RS和LCD_EN清零
	GpioDataRegs.GPACLEAR.bit.GPIO0 = 1;
	GpioDataRegs.GPACLEAR.bit.GPIO1 = 1;

	EDIS;
}

void LCD1602_WriteCmd(unsigned char cmd)
{
	LCD1602_EN_SETL;
	LCD1602_RS_SETL;
	LCD1602_DATAPORT=cmd<<2;
	DELAY_US(500);
	LCD1602_EN_SETH;
	DELAY_US(1000);
	LCD1602_EN_SETL;
}

void LCD1602_WriteData(unsigned char dat)
{
	LCD1602_EN_SETL;
	LCD1602_RS_SETH;
	LCD1602_DATAPORT=dat<<2|0x0001;
	DELAY_US(500);
	LCD1602_EN_SETH;
	DELAY_US(1000);
	LCD1602_EN_SETL;
}

void LCD1602_Init(void)
{
	LCD1602_GPIOInit();

	DELAY_US(15000);//延迟15ms
	LCD1602_WriteCmd(0x38);//设置8位格式，2行，5x7
	DELAY_US(5000);//延迟5ms
	LCD1602_WriteCmd(0x38);//设置8位格式，2行，5x7
	DELAY_US(5000);
	LCD1602_WriteCmd(0x38);//设置8位格式，2行，5x7
	LCD1602_WriteCmd(0x38);//设置8位格式，2行，5x7
	LCD1602_WriteCmd(0x08);//关显示，不显示光标，光标不闪烁；
	LCD1602_WriteCmd(0x01);//清除屏幕显示：数据指针清零，所有显示清零；
	LCD1602_WriteCmd(0x06);//设定输入方式，增量不移位
	LCD1602_WriteCmd(0x0c);//整体显示，关光标，不闪烁
}

void LCD1602_DispString(char line,char *str)
{
	if(line==1)
		LCD1602_WriteCmd(0x80);
	else if(line==2)
		LCD1602_WriteCmd(0x80+0x40);
	else
		return;
	while(*str!='\0')
	{
		LCD1602_WriteData(*str);
		DELAY_US(500);  //延时500us
		str++;
	}
}

void LCD1602_DispStringEx(char line,char x,char *str)
{
	if(line==1)
		LCD1602_WriteCmd(0x80+x);
	else if(line==2)
		LCD1602_WriteCmd(0x80+0x40+x);
	else
		return;
	while(*str!='\0')
	{
		LCD1602_WriteData(*str);
		DELAY_US(500);  //延时500us
		str++;
	}
}
