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



void I2CA_Init(void);


Uint16 AIC23Write(int Address,int Data);
void Delay(int time);


void Mydelay(Uint32 k);

interrupt void  ISRMcbspSend();

/****************端口宏定义*****************/
#define LuYin GpioDataRegs.GPADAT.bit.GPIO12
#define LuYin_ST GpioDataRegs.GPADAT.bit.GPIO13
#define BoYin GpioDataRegs.GPADAT.bit.GPIO14


/*******************************************************************************
* 函 数 名         : main
* 函数功能		   : 主函数
* 输    入         : 无
* 输    出         : 无
*******************************************************************************/
void main()
{
	Uint16 temp,i;


	InitSysCtrl();
	InitPieCtrl();
	IER = 0x0000;
	IFR = 0x0000;
	InitPieVectTable();

	LED_Init();
	TIM0_Init(150,200000);//200ms
	UARTa_Init(4800);

	InitMcbspaGpio();	//zq
	InitI2CGpio();

	I2CA_Init();

	AIC23Write(0x00,0x00);
	Delay(100);
	AIC23Write(0x02,0x00);
	Delay(100);
	AIC23Write(0x04,0x7f);
	Delay(100);
	AIC23Write(0x06,0x7f);
	Delay(100);
	AIC23Write(0x08,0x14);
	Delay(100);
	AIC23Write(0x0A,0x00);
	Delay(100);
	AIC23Write(0x0C,0x00);
	Delay(100);
	AIC23Write(0x0E,0x43);
	Delay(100);
	AIC23Write(0x10,0x23);
	Delay(100);
	AIC23Write(0x12,0x01);
	Delay(100);		//AIC23Init

	InitMcbspa();          // Initalize the Mcbsp-A

	EALLOW;	// This is needed to write to EALLOW protected registers
	PieVectTable.MRINTA = &ISRMcbspSend;
	EDIS;   // This is needed to disable write to EALLOW protected registers

	PieCtrlRegs.PIECTRL.bit.ENPIE = 1;   // Enable the PIE block
	PieCtrlRegs.PIEIER6.bit.INTx5=1;     // Enable PIE Group 6, INT 5
	IER |= M_INT6;                            // Enable CPU INT6

	EINT;   // Enable Global interrupt INTM
	ERTM;	// Enable Global realtime interrupt DBGM

	//发出报警声
	while(1)
	{

	}
}

void I2CA_Init(void)
{
   // Initialize I2C
   I2caRegs.I2CSAR = 0x001A;		// Slave address - EEPROM control code

   #if (CPU_FRQ_150MHZ)             // Default - For 150MHz SYSCLKOUT
        I2caRegs.I2CPSC.all = 14;   // Prescaler - need 7-12 Mhz on module clk (150/15 = 10MHz)
   #endif
   #if (CPU_FRQ_100MHZ)             // For 100 MHz SYSCLKOUT
     I2caRegs.I2CPSC.all = 9;	    // Prescaler - need 7-12 Mhz on module clk (100/10 = 10MHz)
   #endif

   I2caRegs.I2CCLKL = 100;			// NOTE: must be non zero
   I2caRegs.I2CCLKH = 100;			// NOTE: must be non zero
   I2caRegs.I2CIER.all = 0x24;		// Enable SCD & ARDY interrupts

//   I2caRegs.I2CMDR.all = 0x0020;	// Take I2C out of reset
   I2caRegs.I2CMDR.all = 0x0420;	// Take I2C out of reset		//zq
   									// Stop I2C when suspended

   I2caRegs.I2CFFTX.all = 0x6000;	// Enable FIFO mode and TXFIFO
   I2caRegs.I2CFFRX.all = 0x2040;	// Enable RXFIFO, clear RXFFINT,

   return;
}

Uint16 AIC23Write(int Address,int Data)
{


   if (I2caRegs.I2CMDR.bit.STP == 1)
   {
      return I2C_STP_NOT_READY_ERROR;
   }

   // Setup slave address
   I2caRegs.I2CSAR = 0x1A;

   // Check if bus busy
   if (I2caRegs.I2CSTR.bit.BB == 1)
   {
      return I2C_BUS_BUSY_ERROR;
   }

   // Setup number of bytes to send
   // MsgBuffer + Address
   I2caRegs.I2CCNT = 2;
   I2caRegs.I2CDXR = Address;
   I2caRegs.I2CDXR = Data;
   // Send start as master transmitter
   I2caRegs.I2CMDR.all = 0x6E20;
   return I2C_SUCCESS;

}

void Delay(int time)
{
	int i,j,k=0;
	for(i=0;i<time;i++)
		for(j=0;j<1024;j++)
			k++;
}

void Mydelay(Uint32 k)
{
	while(k--);
}

interrupt void  ISRMcbspSend(void)
{
	int temp1,temp2;

	temp1=McbspaRegs.DRR1.all;
	temp2=McbspaRegs.DRR2.all;

	McbspaRegs.DXR1.all = temp1;        //放音
	McbspaRegs.DXR2.all = temp2;

	PieCtrlRegs.PIEACK.all = 0x0020;
	//	PieCtrlRegs.PIEIFR6.bit.INTx5 = 0;
	//	ERTM;

}

