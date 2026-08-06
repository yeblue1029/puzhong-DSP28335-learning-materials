/*
 * can.h
 *
 *  Created on: 2021年5月29日
 *      Author: YZ
 */

#ifndef _CAN_H_
#define _CAN_H_


#include "DSP2833x_Device.h"     // DSP2833x 头文件
#include "DSP2833x_Examples.h"   // DSP2833x 例子相关头文件


void CANB_Init(void);
void CanBSend(Uint32 Can_Id, char length, Uint32 Data_L, Uint32 Data_H);
void CANB_Recv_ISR(void);
#endif /* APP_CAN_CAN_H_ */
