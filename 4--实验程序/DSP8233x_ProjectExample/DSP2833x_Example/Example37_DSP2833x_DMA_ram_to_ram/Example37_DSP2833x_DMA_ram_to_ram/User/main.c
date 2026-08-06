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
#include "dma.h"


#pragma DATA_SECTION(DMABuf1,"DMARAML4");
#pragma DATA_SECTION(DMABuf2,"DMARAML5");

#define DMA_BUF_SIZE 1024
volatile Uint16 DMABuf1[DMA_BUF_SIZE];
volatile Uint16 DMABuf2[DMA_BUF_SIZE];


/*******************************************************************************
* 函 数 名         : main
* 函数功能		   : 主函数
* 输    入         : 无
* 输    出         : 无
*******************************************************************************/
void main()
{
	int i=0;


	InitSysCtrl();
	InitPieCtrl();
	IER = 0x0000;
	IFR = 0x0000;
	InitPieVectTable();

	LED_Init();
	TIM0_Init(150,200000);//200ms
	UARTa_Init(4800);

	// Initialize Tables
	for (i=0; i<DMA_BUF_SIZE; i++)
	{
		DMABuf1[i] = 0;
		DMABuf2[i] = i;
	}

	DMACH1_Init(DMABuf1,DMABuf2);

	while(1)
	{

	}
}

