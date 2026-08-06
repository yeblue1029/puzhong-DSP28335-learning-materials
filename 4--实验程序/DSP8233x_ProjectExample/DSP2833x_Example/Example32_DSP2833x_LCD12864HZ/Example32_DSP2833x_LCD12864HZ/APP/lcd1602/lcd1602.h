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


#define LCD12864_RS_SETH 	(GpioDataRegs.GPASET.bit.GPIO0=1)
#define LCD12864_RS_SETL 	(GpioDataRegs.GPACLEAR.bit.GPIO0=1)

#define LCD12864_EN_SETH 	(GpioDataRegs.GPASET.bit.GPIO1=1)
#define LCD12864_EN_SETL 	(GpioDataRegs.GPACLEAR.bit.GPIO1=1)

#define LCD12864_CS_SETH 	(GpioDataRegs.GPASET.bit.GPIO24=1)
#define LCD12864_CS_SETL 	(GpioDataRegs.GPACLEAR.bit.GPIO24=1)

#define LCD12864_RW_SETH 	(GpioDataRegs.GPBSET.bit.GPIO60=1)
#define LCD12864_RW_SETL 	(GpioDataRegs.GPBCLEAR.bit.GPIO60=1)

#define LCD12864_DATAPORT	(GpioDataRegs.GPADAT.all)



void LCD12864_Init(void);
void LCD12864_DispString(char line,char *str);
void LCD12864_DispStringEx(char line,char x,char *str);

#endif /* LCD1602_H_ */
