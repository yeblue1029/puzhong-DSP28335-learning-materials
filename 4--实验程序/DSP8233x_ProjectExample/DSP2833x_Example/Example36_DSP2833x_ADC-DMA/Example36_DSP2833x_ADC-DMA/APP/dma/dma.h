/*
 * dma.h
 *
 *  Created on: 2018-1-30
 *      Author: Administrator
 */

#ifndef DMA_H_
#define DMA_H_


#include "DSP2833x_Device.h"     // DSP2833x 头文件
#include "DSP2833x_Examples.h"   // DSP2833x 例子相关头文件

//#define DMA_INT_ENABLE

void DMACH1_Init(volatile Uint16 *DMA_Dest,volatile Uint16 *DMA_Source);
interrupt void local_DINTCH1_ISR(void);
void DMACH1_ADC_Init(volatile Uint16 *DMA_Dest,volatile Uint16 *DMA_Source);

#endif /* DMA_H_ */
