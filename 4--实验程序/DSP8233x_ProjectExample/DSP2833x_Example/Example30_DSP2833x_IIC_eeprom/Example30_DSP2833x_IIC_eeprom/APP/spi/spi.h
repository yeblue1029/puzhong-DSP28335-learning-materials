/*
 * spi.h
 *
 *  Created on: 2018-2-3
 *      Author: Administrator
 */

#ifndef SPI_H_
#define SPI_H_


#include "DSP2833x_Device.h"     // DSP2833x 头文件
#include "DSP2833x_Examples.h"   // DSP2833x 例子相关头文件


void SPIA_Init(void);
Uint16 SPIA_SendReciveData(Uint16 dat);


#define SPIA_TXRX_INT_FIFO

void SPIA_INTFIFO_Test(void);

#endif /* SPI_H_ */
