/*
 * can.c
 *
 *  Created on: 2021年5月29日
 *      Author: YZ
 */

#include "can.h"

void CANB_Init(void)
{
    struct ECAN_REGS ECanbShadow;

    InitECanbGpio();
    InitECanb();

    /* Configure Mailbox under test as a Transmit mailbox */
    ECanbShadow.CANMD.all = ECanbRegs.CANMD.all;
    ECanbShadow.CANMD.all = 0xff00;//邮箱0~7为发送，8~15为接收
    ECanbRegs.CANMD.all = ECanbShadow.CANMD.all;

    ECanbShadow.CANGAM.all = ECanbRegs.CANGAM.all;
    ECanbShadow.CANGAM.bit.AMI = 1;    //标准帧和扩展帧都接受
    ECanbShadow.CANGAM.bit.GAM2816 |= 0x1fff; //LAM(0)用于邮箱0~2 ,LAM(3)用于邮箱3~5,对于邮箱6~15,用全局接收屏蔽
    ECanbRegs.CANGAM.all = ECanbShadow.CANGAM.all;


    //接收中断设置
    EALLOW;
    ECanbShadow.CANMIM.all = ECanbRegs.CANMIM.all;
    ECanbShadow.CANMIM.all = 0xff00 ;              // 开启8~15号邮箱中断
    ECanbRegs.CANMIM.all = ECanbShadow.CANMIM.all;
    ECanbShadow.CANMIL.all = ECanbRegs.CANMIL.all;
    ECanbShadow.CANMIL.all = 0xff00 ;              // 8~15号邮箱中断在中断线1上产生
    ECanbRegs.CANMIL.all = ECanbShadow.CANMIL.all;
    ECanbShadow.CANGIM.all = ECanbRegs.CANGIM.all;
    ECanbShadow.CANGIM.all = 0x02 ;              //  中断线1使能
    ECanbRegs.CANGIM.all = ECanbShadow.CANGIM.all;
    EDIS;

    //ECanbMboxes.MBOX15.MSGID.bit.AME=1;  //15号邮箱接收任何ID的报文
    ECanbMboxes.MBOX5.MSGID.all = 0; // stand Identifier
    /* Enable Mailbox under test */
    ECanbShadow.CANME.all = ECanbRegs.CANME.all;
    ECanbShadow.CANME.all = 0xffff;
    ECanbRegs.CANME.all = ECanbShadow.CANME.all;

}


//注意邮箱编号需要根据实际修改
//CANB 发送函数 Can_Id为11位标准帧ID, length为CAN数据长度(单位是字节), Data_L为低四位字节，Data_H为高四位字节
void CanBSend(Uint32 Can_Id, char length, Uint32 Data_L, Uint32 Data_H)
{
    struct ECAN_REGS ECanbShadow;

    //修改ID前要禁止邮箱才能往寄存器里面写值
    ECanbShadow.CANME.all = ECanbRegs.CANME.all;
    ECanbShadow.CANME.all = 0;
    ECanbRegs.CANME.all = ECanbShadow.CANME.all;
     /* Write to the MSGID field  */
    ECanbMboxes.MBOX5.MSGID.all = ( (Can_Id|0x10000000)<<18); // stand Identifier
    //使能邮箱
    ECanbShadow.CANME.all = ECanbRegs.CANME.all;
    ECanbShadow.CANME.all = 0xffff;
    ECanbRegs.CANME.all = ECanbShadow.CANME.all;

    /* Write to DLC field in Master Control reg */
    ECanbMboxes.MBOX5.MSGCTRL.bit.DLC = length; //8;
    /* Write to the mailbox RAM field */
    ECanbMboxes.MBOX5.MDL.all =Data_L;  // 0x54555555; //高位4字节
    ECanbMboxes.MBOX5.MDH.all =Data_H ;  // 0x55578555; //低位4字节


    //struct ECAN_REGS ECanbShadow;
    ECanbShadow.CANTRS.all = 0;
    ECanbShadow.CANTRS.bit.TRS5 = 1;             // Set TRS for mailbox under test
    ECanbRegs.CANTRS.all = ECanbShadow.CANTRS.all;
    do
    {
        ECanbShadow.CANTA.all = ECanbRegs.CANTA.all;
    }while(ECanbShadow.CANTA.bit.TA5 == 0 );   // Wait for TA5 bit to be set..
    ECanbShadow.CANTA.all = 0;
    ECanbShadow.CANTA.bit.TA5 = 1;             // Clear TA5
    ECanbRegs.CANTA.all = ECanbShadow.CANTA.all;
}

Uint32  Mbox_DL = 0;
Uint32  Mbox_DH = 0;
Uint32  Mbox_MSGID = 0;
Uint32 ttt=0;

void CANB_Recv_ISR(void)     // CANB接收中断
{
    struct ECAN_REGS ECanbShadow;
    volatile struct MBOX *Mailbox;
    PieCtrlRegs.PIEACK.all = PIEACK_GROUP9;

    ttt=(ECanbRegs.CANGIF1.all)&0x0f;
    Mailbox = &ECanbMboxes.MBOX0 + ttt;    //邮箱0地址+邮箱中断向量得到偏移地址
    Mbox_DL = Mailbox->MDL.all;           // = 0x9555AAAn (n is the MBX number)
    Mbox_DH = Mailbox->MDH.all;           // = 0x89ABCDEF (a constant)
    Mbox_MSGID = ((Mailbox->MSGID.all)&0X1FFC0000)>>18;      // = 0x9555AAAn (n is the MBX number)

    ECanbShadow.CANGIF1.all = ECanbRegs.CANGIF1.all;
    ECanbShadow.CANGIF1.bit.GMIF1 = 1;             //清除中断标志位
    ECanbRegs.CANGIF1.all = ECanbShadow.CANGIF1.all;
    ECanbRegs.CANRMP.all = 0XFF00;  //清中断接收标志
}



