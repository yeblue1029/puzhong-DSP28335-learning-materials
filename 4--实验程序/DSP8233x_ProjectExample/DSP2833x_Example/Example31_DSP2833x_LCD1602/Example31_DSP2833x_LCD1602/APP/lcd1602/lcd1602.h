/*
 * lcd1602.h
 *
 *  Created on: 2018-2-28
 *      Author: Administrator
 */

#ifndef LCD1602_H_
#define LCD1602_H_

#include "DSP2833x_Device.h"     // DSP2833x Headerfile Include File
#include "DSP2833x_Examples.h"   // DSP2833x Examples Include File


#define LCD1602_RS_SETH 	(GpioDataRegs.GPASET.bit.GPIO0=1)
#define LCD1602_RS_SETL 	(GpioDataRegs.GPACLEAR.bit.GPIO0=1)

#define LCD1602_EN_SETH 	(GpioDataRegs.GPASET.bit.GPIO1=1)
#define LCD1602_EN_SETL 	(GpioDataRegs.GPACLEAR.bit.GPIO1=1)

#define LCD1602_DATAPORT	(GpioDataRegs.GPADAT.all)


void LCD1602_Init(void);
void LCD1602_DispString(char line,char *str);
void LCD1602_DispStringEx(char line,char x,char *str);

#endif /* LCD1602_H_ */
