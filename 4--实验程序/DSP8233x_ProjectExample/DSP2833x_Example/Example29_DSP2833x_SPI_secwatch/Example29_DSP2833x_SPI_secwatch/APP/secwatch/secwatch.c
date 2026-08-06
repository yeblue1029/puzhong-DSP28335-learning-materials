/*
 * secwatch.c
 *
 *  Created on: 2018-2-3
 *      Author: Administrator
 */

#include "secwatch.h"
#include "smg.h"
#include "spi.h"

extern unsigned char smgduan[16];

void SECWatch_Display(unsigned char sec,unsigned char mms)
{
	unsigned char buf[4];
	unsigned char i=0;

	buf[0]=smgduan[sec/10];
	buf[1]=smgduan[sec%10]|0x80;
	buf[2]=smgduan[mms/10];
	buf[3]=smgduan[mms%10];

	for(i=0;i<4;i++)
	{
		SPIA_SendReciveData(buf[i]);
		switch(i)
		{
			case 0: SEG1_SETH;SEG2_SETL;SEG3_SETL;SEG4_SETL;break;
			case 1: SEG1_SETL;SEG2_SETH;SEG3_SETL;SEG4_SETL;break;
			case 2: SEG1_SETL;SEG2_SETL;SEG3_SETH;SEG4_SETL;break;
			case 3: SEG1_SETL;SEG2_SETL;SEG3_SETL;SEG4_SETH;break;
		}
		DELAY_US(5000);
	}
}
