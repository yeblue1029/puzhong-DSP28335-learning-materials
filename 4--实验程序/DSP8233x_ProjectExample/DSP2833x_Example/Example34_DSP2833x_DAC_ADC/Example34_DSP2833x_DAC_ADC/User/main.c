/*
 * main.c
 *
 *  Created on: 2018-3-21
 *      Author: Administrator
 */
//使用一根短接线，将DAC模块的DB输出口与P8排针的ADA0管脚连接。

#include "DSP2833x_Device.h"     // DSP2833x Headerfile Include File
#include "DSP2833x_Examples.h"   // DSP2833x Examples Include File

#include "leds.h"
#include "time.h"
#include "uart.h"
#include "stdio.h"
#include "tlv5620.h"
#include "adc.h"

/*******************************************************************************
* 函 数 名         : main
* 函数功能		   : 主函数
* 输    入         : 无
* 输    出         : 无
*******************************************************************************/
void main()
{
	int i=0;
	Uint16 dacvalue=64;
	float dac_vol;
	Uint16 dac_temp=0;
	char dacbuf[6];

	float adc_vol;
	Uint16 adc_temp=0;


	InitSysCtrl();
	InitPieCtrl();
	IER = 0x0000;
	IFR = 0x0000;
	InitPieVectTable();

	LED_Init();
	TIM0_Init(150,200000);//200ms
	UARTa_Init(4800);
	TLV5620_Init();
	ADC_Init();

	while(1)
	{
		i++;
		if(i%1000==0)
		{

			DAC_SetChannelData(1,0,dacvalue*2);
			dac_vol=dacvalue*2*1.9/255;
			dac_temp=dac_vol*100;
			dacbuf[0]=dac_temp/100+0x30;
			dacbuf[1]='.';
			dacbuf[2]=dac_temp%100/10+0x30;
			dacbuf[3]=dac_temp%100%10+0x30;
			dacbuf[4]='V';
			dacbuf[5]='\0';
			UARTa_SendString("\r\nCH2_VOL=");
			UARTa_SendString(dacbuf);

			adc_vol=(float)Read_ADCValue()*3.3/4095;
			adc_temp=adc_vol*100;
			dacbuf[0]=adc_temp/100+0x30;
			dacbuf[1]='.';
			dacbuf[2]=adc_temp%100/10+0x30;
			dacbuf[3]=adc_temp%100%10+0x30;
			dacbuf[4]='V';
			dacbuf[5]='\0';
			UARTa_SendString("\r\nADC_CH1_VOL=");
			UARTa_SendString(dacbuf);
		}
		DELAY_US(1*1000);
	}
}

