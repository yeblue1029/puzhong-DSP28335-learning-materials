/*
 * main.c
 *
 *  Created on: 2018-3-21
 *      Author: Administrator
 */


#include "DSP2833x_Device.h"     // DSP2833x Headerfile Include File
#include "DSP2833x_Examples.h"   // DSP2833x Examples Include File

#include "leds.h"
#include "time.h"
#include "uart.h"
#include "stdio.h"
#include "key.h"
#include "relay.h"
#include "smg.h"
#include "adc.h"
#include "tlv5620.h"
#include "dc_motor.h"
#include "step_motor.h"
#include "24cxx.h"
#include "aic23.h"
#include "lcd1602.h"
#include "lcd12864.h"
#include "dma.h"

extern char KEYValue;
/*******************************************************************************
* 函 数 名         : main
* 函数功能		   : 主函数
* 输    入         : 无
* 输    出         : 无
*******************************************************************************/
void main()
{
	Uint16 i=0;
	Uint16 dacvalue=64;
	float dac_vol;
	Uint16 dac_temp=0;
	char dacbuf[6];


	InitSysCtrl();
	InitPieCtrl();
	IER = 0x0000;
	IFR = 0x0000;
	InitPieVectTable();

	//复制对时间敏感代码和FLASH配置代码到RAM中
	// 包括FLASH初始化函数 InitFlash();
	// 链接后将产生 RamfuncsLoadStart, RamfuncsLoadEnd, 和RamfuncsRunStart
	// 参数. 请参考 F28335.cmd 文件
	MemCopy(&RamfuncsLoadStart, &RamfuncsLoadEnd, &RamfuncsRunStart);
	// 调用FLASH初始化函数来设置flash等待状态
	// 这个函数必须在RAM中运行
	InitFlash();

	LED_Init();
	TIM0_Init(150,30000);//30ms
	UARTa_Init(4800);
	//RS232模块测试
	UARTa_SendString("Hello PRECHIN!\r\n");

	//EEPROM模块测试
	AT24CXX_Init();
	while(AT24CXX_Check())  //检测AT24C02是否正常
	{
		UARTa_SendString("AT24C02检测不正常!\r\n");
		DELAY_US(100*1000);
		LED1_TOGGLE;
	}
	UARTa_SendString("AT24C02检测正常!\r\n");

	//DAC模块测试
	TLV5620_Init();
	DAC_SetChannelData(0,0,dacvalue);
	dac_vol=dacvalue*1.9/255;
	dac_temp=dac_vol*100;
	dacbuf[0]=dac_temp/100+0x30;
	dacbuf[1]='.';
	dacbuf[2]=dac_temp%100/10+0x30;
	dacbuf[3]=dac_temp%100%10+0x30;
	dacbuf[4]='V';
	dacbuf[5]='\0';
	UARTa_SendString("\r\nCH1_VOL=");
	UARTa_SendString(dacbuf);

	KEY_Init();


	while(1)
	{
		switch(KEYValue)
		{
			case KEY1_PRESS: LED_Test();break;//LED测试
			case KEY2_PRESS: BEEP_Test();break;//蜂鸣器/继电器测试
			case KEY3_PRESS: ADC_Test();break;//ADC/数码管测试
			case KEY4_PRESS: DCMotor_Test();break;//直流电机模块测试
			case KEY5_PRESS: STEPMotor_Test();break;//步进电机模块测试
			case KEY6_PRESS: AIC23_Test();break;//音频模块测试
			case KEY7_PRESS: LCD1602_Test();break;//LCD1602测试
			case KEY8_PRESS: SRAM_Test();break;//SRAM测试
			case KEY9_PRESS: LCD12864_Test();break;//LCD12864测试

		}
	}
}

