/*
 * adc.h
 *
 *  Created on: 2018-1-29
 *      Author: Administrator
 */

#ifndef ADC_H_
#define ADC_H_

#include "DSP2833x_Device.h"     // DSP2833x 头文件
#include "DSP2833x_Examples.h"   // DSP2833x 例子相关头文件



#define ADC_MODCLK 3

#define BUF_SIZE   16  // Sample buffer size
extern Uint16 SampleTable[BUF_SIZE];


void ADC_Init(void);
Uint16 Read_ADC_CH0_Value(void);
void Read_ADC_SEQ1_Value_OVD(void);
interrupt void  adc_isr(void);


#endif /* ADC_H_ */
