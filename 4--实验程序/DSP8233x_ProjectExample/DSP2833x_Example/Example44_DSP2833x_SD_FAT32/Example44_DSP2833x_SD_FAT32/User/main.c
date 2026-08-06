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




extern	void play_Udisc();

/*******************************************************************************
* 函 数 名         : main
* 函数功能		   : 主函数
* 输    入         : 无
* 输    出         : 无
*******************************************************************************/
void main()
{
	Uint16 i=0;


	InitSysCtrl();
	InitPieCtrl();
	IER = 0x0000;
	IFR = 0x0000;
	InitPieVectTable();

	LED_Init();
	TIM0_Init(150,200000);//200ms
	UARTa_Init(4800);

	InitXintf();
	InitSpiaGpio();

	spi_initialization();					//Initialize SPI

	sd_card_insertion();			//Check for card insertion
	sd_initialization();			//Initialize card

	sd_read_register(SEND_CSD);		//Read CSD register
	sd_read_register(READ_OCR);		//Read OCR register
	sd_read_register(SEND_CID);		//Read CID register

	play_Udisc();

	asm("     ESTOP0");  // test failed!! Stop!

	while(1)
	{

	}
}

