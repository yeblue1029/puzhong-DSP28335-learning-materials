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
#include "key.h"
#include "can.h"

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

	//复制对时间敏感代码和FLASH配置代码到RAM中
	// 包括FLASH初始化函数 InitFlash();
	// 链接后将产生 RamfuncsLoadStart, RamfuncsLoadEnd, 和RamfuncsRunStart
	// 参数. 请参考 F28335.cmd 文件
	MemCopy(&RamfuncsLoadStart, &RamfuncsLoadEnd, &RamfuncsRunStart);
	// 调用FLASH初始化函数来设置flash等待状态
	// 这个函数必须在RAM中运行
	InitFlash();

	LED_Init();
	TIM0_Init(150,300000);//300ms
	UARTa_Init(4800);
	KEY_Init();
	//RS232模块测试
	UARTa_SendString("Hello PRECHIN!\r\n");
	CANB_Init();

	while(1)
	{
	    i++;
	    if(i%100==0)
	    {
	        LED2_TOGGLE;
	        CanBSend(0x22,8,0x0101,0x0202);
	    }
	    DELAY_US(10000);
	}
}

