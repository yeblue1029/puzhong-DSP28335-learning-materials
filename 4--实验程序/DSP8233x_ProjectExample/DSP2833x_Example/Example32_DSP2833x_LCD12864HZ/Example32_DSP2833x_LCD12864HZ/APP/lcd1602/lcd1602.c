/*
 * lcd1602.c
 *
 *  Created on: 2018-2-28
 *      Author: Administrator
 */

#include "lcd1602.h"


void LCD12864_GPIOInit(void)
{
	EALLOW;
	SysCtrlRegs.PCLKCR3.bit.GPIOINENCLK = 1;// 开启GPIO时钟
	GpioCtrlRegs.GPAPUD.bit.GPIO0 = 0;    // 使能GPIO0 引脚内部上拉
	GpioCtrlRegs.GPAPUD.bit.GPIO1 = 0;   // 禁止GPIO1 引脚内部上拉
	GpioCtrlRegs.GPAPUD.bit.GPIO24 = 0;
	GpioCtrlRegs.GPBPUD.bit.GPIO60 = 0;

	GpioCtrlRegs.GPAMUX1.all = 0;   // 配置GPIO0-GPIO15为通用I/O口
	GpioCtrlRegs.GPAMUX2.bit.GPIO24 = 0;
	GpioCtrlRegs.GPBMUX2.bit.GPIO60 = 0;

	GpioCtrlRegs.GPADIR.all = 0x00FFF;// 配置GPIO0-GPIO11为输出引脚
	GpioCtrlRegs.GPADIR.bit.GPIO24=1;
	GpioCtrlRegs.GPBDIR.bit.GPIO60=1;

	// 每个输入口可以有不同的输入限定
	// a) 输入与系统时钟 SYSCLKOUT同步
	// b) 输入被指定的采样窗口限定
	// c) 输入异步 (仅对外设输入有效)
	GpioCtrlRegs.GPAQSEL1.all = 0x0000;    // GPIO0-GPIO15与系统时钟SYSCLKOUT 同步
	GpioCtrlRegs.GPAQSEL2.bit.GPIO24=0;
	GpioCtrlRegs.GPBQSEL2.bit.GPIO60=0;

	//输出数据LCD_RS和LCD_EN清零
	GpioDataRegs.GPACLEAR.bit.GPIO0 = 1;
	GpioDataRegs.GPACLEAR.bit.GPIO1 = 1;
	GpioDataRegs.GPACLEAR.bit.GPIO24 = 1;
	GpioDataRegs.GPBCLEAR.bit.GPIO60 = 1;

	EDIS;
}

void LCD12864_WriteCmd(unsigned char cmd)
{
	LCD12864_RS_SETL;
	LCD12864_EN_SETH;
	LCD12864_DATAPORT=(cmd<<2)|0x02;
	DELAY_US(10000);
	LCD12864_EN_SETL;
	DELAY_US(100);
}

void LCD12864_WriteData(unsigned char dat)
{
	LCD12864_RS_SETH;
	LCD12864_EN_SETH;
	LCD12864_DATAPORT=(dat<<2)|0x03;
	DELAY_US(10000);
	LCD12864_EN_SETL;
	DELAY_US(100);
}

void LCD12864_Init(void)
{
	LCD12864_GPIOInit();
	LCD12864_RW_SETL;
	LCD12864_CS_SETH;

	DELAY_US(15000);//延迟15ms
	LCD12864_WriteCmd(0x38);//设置8位格式，2行，5x7
	DELAY_US(5000);//延迟5ms
	LCD12864_WriteCmd(0x38);//设置8位格式，2行，5x7
	DELAY_US(5000);
	LCD12864_WriteCmd(0x38);//设置8位格式，2行，5x7
	LCD12864_WriteCmd(0x38);//设置8位格式，2行，5x7
	LCD12864_WriteCmd(0x08);//关显示，不显示光标，光标不闪烁；
	LCD12864_WriteCmd(0x01);//清除屏幕显示：数据指针清零，所有显示清零；
	LCD12864_WriteCmd(0x06);//设定输入方式，增量不移位
	LCD12864_WriteCmd(0x0c);//整体显示，关光标，不闪烁
	LCD12864_WriteCmd(0x80);
}

void LCD12864_DispString(char line,char *str)
{
	if(line==1)
		LCD12864_WriteCmd(0x80);
	else if(line==2)
		LCD12864_WriteCmd(0x90);
	else if(line==3)
		LCD12864_WriteCmd(0x88);
	else if(line==4)
		LCD12864_WriteCmd(0x98);
	else
		return;
	while(*str!='\0')
	{
		LCD12864_WriteData(*str);
		DELAY_US(500);  //延时500us
		str++;
	}
}

void LCD12864_DispStringEx(char line,char x,char *str)
{
	if(line==1)
		LCD12864_WriteCmd(0x80+x);
	else if(line==2)
		LCD12864_WriteCmd(0x90+x);
	else if(line==3)
		LCD12864_WriteCmd(0x88+x);
	else if(line==4)
		LCD12864_WriteCmd(0x98+x);
	else
		return;
	while(*str!='\0')
	{
		LCD12864_WriteData(*str);
		DELAY_US(500);  //延时500us
		str++;
	}
}
