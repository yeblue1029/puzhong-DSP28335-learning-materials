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
#include "tlv5620.h"



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


	InitSysCtrl();
	InitPieCtrl();
	IER = 0x0000;
	IFR = 0x0000;
	InitPieVectTable();

	LED_Init();
	TIM0_Init(150,200000);//200ms
	UARTa_Init(4800);
	TLV5620_Init();

	while(1)
	{
		i++;
		if(i%1000==0)
		{
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

			DAC_SetChannelData(2,0,dacvalue*3);
			dac_vol=dacvalue*3*1.9/255;
			dac_temp=dac_vol*100;
			dacbuf[0]=dac_temp/100+0x30;
			dacbuf[1]='.';
			dacbuf[2]=dac_temp%100/10+0x30;
			dacbuf[3]=dac_temp%100%10+0x30;
			dacbuf[4]='V';
			dacbuf[5]='\0';
			UARTa_SendString("\r\nCH3_VOL=");
			UARTa_SendString(dacbuf);

			DAC_SetChannelData(3,0,dacvalue*4-1);
			dac_vol=dacvalue*4*1.9/255;
			dac_temp=dac_vol*100;
			dacbuf[0]=dac_temp/100+0x30;
			dacbuf[1]='.';
			dacbuf[2]=dac_temp%100/10+0x30;
			dacbuf[3]=dac_temp%100%10+0x30;
			dacbuf[4]='V';
			dacbuf[5]='\0';
			UARTa_SendString("\r\nCH4_VOL=");
			UARTa_SendString(dacbuf);
		}
		DELAY_US(1*1000);
	}
}

