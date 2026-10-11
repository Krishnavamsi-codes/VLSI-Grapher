/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : O-2018.06-SP5-5
// Date      : Sat Sep 26 03:10:33 2020
/////////////////////////////////////////////////////////////


module add_mul_mix_4_bit ( a, b, c, d, Result );
  input [0:3] a;
  input [0:3] b;
  input [0:3] c;
  input [0:3] d;
  output [0:7] Result;
  wire   \adder_1/n27 , \adder_1/n26 , \adder_1/n25 , \adder_1/n24 ,
         \adder_1/n23 , \adder_1/n22 , \adder_1/n21 , \adder_1/n20 ,
         \adder_1/n19 , \adder_1/n18 , \adder_1/n17 , \adder_1/n16 ,
         \adder_1/n15 , \adder_1/n14 , \adder_1/n13 , \adder_1/n12 ,
         \adder_1/n11 , \adder_1/n10 , \adder_1/n9 , \adder_1/n8 ,
         \adder_1/n7 , \adder_1/n6 , \adder_1/n5 , \adder_1/n4 , \adder_1/n3 ,
         \adder_1/n2 , \adder_1/n1 , \adder_2/n16 , \adder_2/n15 ,
         \adder_2/n14 , \adder_2/n13 , \adder_2/n12 , \adder_2/n11 ,
         \adder_2/n10 , \adder_2/n9 , \adder_2/n8 , \adder_2/n7 , \adder_2/n6 ,
         \adder_2/n5 , \adder_2/n4 , \adder_2/n3 , \adder_2/n2 , \adder_2/n1 ,
         \multiplier_1/n90 , \multiplier_1/n89 , \multiplier_1/n88 ,
         \multiplier_1/n87 , \multiplier_1/n86 , \multiplier_1/n85 ,
         \multiplier_1/n84 , \multiplier_1/n83 , \multiplier_1/n82 ,
         \multiplier_1/n81 , \multiplier_1/n80 , \multiplier_1/n79 ,
         \multiplier_1/n78 , \multiplier_1/n77 , \multiplier_1/n76 ,
         \multiplier_1/n75 , \multiplier_1/n74 , \multiplier_1/n73 ,
         \multiplier_1/n72 , \multiplier_1/n71 , \multiplier_1/n70 ,
         \multiplier_1/n69 , \multiplier_1/n68 , \multiplier_1/n67 ,
         \multiplier_1/n66 , \multiplier_1/n65 , \multiplier_1/n64 ,
         \multiplier_1/n63 , \multiplier_1/n62 , \multiplier_1/n61 ,
         \multiplier_1/n60 , \multiplier_1/n59 , \multiplier_1/n58 ,
         \multiplier_1/n57 , \multiplier_1/n56 , \multiplier_1/n55 ,
         \multiplier_1/n54 , \multiplier_1/n53 , \multiplier_1/n52 ,
         \multiplier_1/n51 , \multiplier_1/n50 , \multiplier_1/n49 ,
         \multiplier_1/n48 , \multiplier_1/n47 , \multiplier_1/n46 ,
         \multiplier_1/n45 , \multiplier_1/n44 , \multiplier_1/n43 ,
         \multiplier_1/n42 , \multiplier_1/n41 , \multiplier_1/n40 ,
         \multiplier_1/n39 , \multiplier_1/n38 , \multiplier_1/n37 ,
         \multiplier_1/n36 , \multiplier_1/n35 , \multiplier_1/n34 ,
         \multiplier_1/n33 , \multiplier_1/n32 , \multiplier_1/n31 ,
         \multiplier_1/n30 , \multiplier_1/n29 , \multiplier_1/n28 ,
         \multiplier_1/n27 , \multiplier_1/n26 , \multiplier_1/n25 ,
         \multiplier_1/n24 , \multiplier_1/n23 , \multiplier_1/n22 ,
         \multiplier_1/n21 , \multiplier_1/n20 , \multiplier_1/n19 ,
         \multiplier_1/n18 , \multiplier_1/n17 , \multiplier_1/n16 ,
         \multiplier_1/n15 , \multiplier_1/n14 , \multiplier_1/n13 ,
         \multiplier_1/n12 , \multiplier_1/n11 , \multiplier_1/n10 ,
         \multiplier_1/n9 , \multiplier_1/n8 , \multiplier_1/n7 ,
         \multiplier_1/n6 , \multiplier_1/n5 , \multiplier_1/n4 ,
         \multiplier_1/n3 , \multiplier_1/n2 , \multiplier_1/n1 ;
  wire   [0:3] Result_add;
  wire   [0:3] Result_add_2;

  NOR2_X2A_A9TH \adder_1/U31  ( .A(\adder_1/n26 ), .B(\adder_1/n25 ), .Y(
        Result_add[3]) );
  INV_X7P5M_A9TH \adder_1/U30  ( .A(a[2]), .Y(\adder_1/n23 ) );
  INV_X16M_A9TH \adder_1/U29  ( .A(b[2]), .Y(\adder_1/n24 ) );
  INV_X16M_A9TH \adder_1/U28  ( .A(a[0]), .Y(\adder_1/n19 ) );
  OAI21_X3M_A9TH \adder_1/U27  ( .A0(\adder_1/n17 ), .A1(\adder_1/n27 ), .B0(
        \adder_1/n21 ), .Y(\adder_1/n14 ) );
  MXIT2_X3M_A9TH \adder_1/U26  ( .A(\adder_1/n14 ), .B(\adder_1/n17 ), .S0(
        \adder_1/n18 ), .Y(\adder_1/n13 ) );
  AOI22_X8M_A9TH \adder_1/U25  ( .A0(\adder_1/n22 ), .A1(\adder_1/n19 ), .B0(
        b[0]), .B1(a[0]), .Y(\adder_1/n18 ) );
  NAND2_X3M_A9TH \adder_1/U24  ( .A(\adder_1/n1 ), .B(\adder_1/n16 ), .Y(
        \adder_1/n15 ) );
  INV_X4M_A9TH \adder_1/U23  ( .A(\adder_1/n20 ), .Y(Result_add[2]) );
  NAND3_X4A_A9TH \adder_1/U22  ( .A(\adder_1/n11 ), .B(\adder_1/n18 ), .C(
        \adder_1/n9 ), .Y(\adder_1/n12 ) );
  XOR2_X4M_A9TH \adder_1/U21  ( .A(a[2]), .B(b[2]), .Y(\adder_1/n8 ) );
  NAND2_X8M_A9TH \adder_1/U20  ( .A(b[3]), .B(a[3]), .Y(\adder_1/n7 ) );
  XOR2_X3M_A9TH \adder_1/U19  ( .A(\adder_1/n8 ), .B(\adder_1/n7 ), .Y(
        \adder_1/n20 ) );
  XOR2_X4M_A9TH \adder_1/U18  ( .A(\adder_1/n6 ), .B(a[1]), .Y(\adder_1/n5 )
         );
  OAI2XB1_X4M_A9TH \adder_1/U17  ( .A1N(\adder_1/n27 ), .A0(\adder_1/n1 ), 
        .B0(\adder_1/n5 ), .Y(\adder_1/n4 ) );
  INV_X4M_A9TH \adder_1/U16  ( .A(\adder_1/n7 ), .Y(\adder_1/n26 ) );
  NOR2_X4M_A9TH \adder_1/U15  ( .A(\adder_1/n18 ), .B(\adder_1/n17 ), .Y(
        \adder_1/n16 ) );
  NAND3_X4M_A9TH \adder_1/U14  ( .A(\adder_1/n15 ), .B(\adder_1/n13 ), .C(
        \adder_1/n12 ), .Y(Result_add[0]) );
  NAND2_X8M_A9TH \adder_1/U13  ( .A(\adder_1/n26 ), .B(\adder_1/n10 ), .Y(
        \adder_1/n9 ) );
  NAND3_X6M_A9TH \adder_1/U12  ( .A(\adder_1/n9 ), .B(\adder_1/n3 ), .C(
        \adder_1/n27 ), .Y(\adder_1/n2 ) );
  INV_X4M_A9TH \adder_1/U11  ( .A(\adder_1/n5 ), .Y(\adder_1/n3 ) );
  NAND2_X8M_A9TH \adder_1/U10  ( .A(\adder_1/n4 ), .B(\adder_1/n2 ), .Y(
        Result_add[1]) );
  NAND2_X6M_A9TH \adder_1/U9  ( .A(\adder_1/n23 ), .B(\adder_1/n24 ), .Y(
        \adder_1/n10 ) );
  INV_X4M_A9TH \adder_1/U8  ( .A(b[1]), .Y(\adder_1/n6 ) );
  INV_X7P5M_A9TH \adder_1/U7  ( .A(b[0]), .Y(\adder_1/n22 ) );
  NAND2_X3A_A9TH \adder_1/U6  ( .A(b[1]), .B(a[1]), .Y(\adder_1/n21 ) );
  NOR2_X6M_A9TH \adder_1/U5  ( .A(b[1]), .B(a[1]), .Y(\adder_1/n17 ) );
  NAND2_X6M_A9TH \adder_1/U4  ( .A(b[2]), .B(a[2]), .Y(\adder_1/n27 ) );
  INV_X6M_A9TH \adder_1/U3  ( .A(\adder_1/n9 ), .Y(\adder_1/n1 ) );
  NOR2_X1A_A9TH \adder_1/U2  ( .A(a[3]), .B(b[3]), .Y(\adder_1/n25 ) );
  AND2_X3M_A9TH \adder_1/U1  ( .A(\adder_1/n27 ), .B(\adder_1/n21 ), .Y(
        \adder_1/n11 ) );
  NOR2_X4M_A9TH \adder_2/U20  ( .A(\adder_2/n14 ), .B(\adder_2/n13 ), .Y(
        \adder_2/n12 ) );
  XOR2_X4M_A9TH \adder_2/U19  ( .A(\adder_2/n12 ), .B(\adder_2/n11 ), .Y(
        Result_add_2[1]) );
  XOR2_X4M_A9TH \adder_2/U18  ( .A(d[2]), .B(c[2]), .Y(\adder_2/n8 ) );
  INV_X1P7M_A9TH \adder_2/U17  ( .A(\adder_2/n10 ), .Y(\adder_2/n16 ) );
  XNOR2_X4M_A9TH \adder_2/U16  ( .A(\adder_2/n8 ), .B(\adder_2/n16 ), .Y(
        \adder_2/n7 ) );
  XNOR2_X4M_A9TH \adder_2/U15  ( .A(\adder_2/n4 ), .B(\adder_2/n3 ), .Y(
        Result_add_2[0]) );
  OAI22_X6M_A9TH \adder_2/U14  ( .A0(d[1]), .A1(c[1]), .B0(\adder_2/n14 ), 
        .B1(\adder_2/n5 ), .Y(\adder_2/n4 ) );
  XOR2_X4M_A9TH \adder_2/U13  ( .A(\adder_2/n2 ), .B(c[1]), .Y(\adder_2/n11 )
         );
  NAND2_X4M_A9TH \adder_2/U12  ( .A(\adder_2/n9 ), .B(\adder_2/n6 ), .Y(
        \adder_2/n5 ) );
  NAND2_X4A_A9TH \adder_2/U11  ( .A(d[1]), .B(c[1]), .Y(\adder_2/n6 ) );
  NOR2_X3M_A9TH \adder_2/U10  ( .A(\adder_2/n16 ), .B(\adder_2/n15 ), .Y(
        Result_add_2[3]) );
  NOR2_X8M_A9TH \adder_2/U9  ( .A(d[2]), .B(c[2]), .Y(\adder_2/n1 ) );
  NAND2_X8M_A9TH \adder_2/U8  ( .A(c[3]), .B(d[3]), .Y(\adder_2/n10 ) );
  NOR2_X8M_A9TH \adder_2/U7  ( .A(\adder_2/n1 ), .B(\adder_2/n10 ), .Y(
        \adder_2/n14 ) );
  NAND2_X6A_A9TH \adder_2/U6  ( .A(d[2]), .B(c[2]), .Y(\adder_2/n9 ) );
  INV_X5M_A9TH \adder_2/U5  ( .A(d[1]), .Y(\adder_2/n2 ) );
  INV_X1M_A9TH \adder_2/U4  ( .A(\adder_2/n9 ), .Y(\adder_2/n13 ) );
  NOR2_X1A_A9TH \adder_2/U3  ( .A(c[3]), .B(d[3]), .Y(\adder_2/n15 ) );
  XOR2_X3M_A9TH \adder_2/U2  ( .A(d[0]), .B(c[0]), .Y(\adder_2/n3 ) );
  INV_X4M_A9TH \adder_2/U1  ( .A(\adder_2/n7 ), .Y(Result_add_2[2]) );
  INV_X0P8M_A9TH \multiplier_1/U98  ( .A(\multiplier_1/n88 ), .Y(
        \multiplier_1/n89 ) );
  OAI21_X1M_A9TH \multiplier_1/U97  ( .A0(\multiplier_1/n86 ), .A1(
        \multiplier_1/n85 ), .B0(\multiplier_1/n84 ), .Y(Result[0]) );
  AOI21_X1M_A9TH \multiplier_1/U96  ( .A0(\multiplier_1/n83 ), .A1(
        \multiplier_1/n82 ), .B0(\multiplier_1/n81 ), .Y(\multiplier_1/n84 )
         );
  XNOR2_X0P5M_A9TH \multiplier_1/U95  ( .A(\multiplier_1/n74 ), .B(
        \multiplier_1/n73 ), .Y(Result[5]) );
  XNOR2_X0P7M_A9TH \multiplier_1/U94  ( .A(\multiplier_1/n68 ), .B(
        \multiplier_1/n67 ), .Y(Result[1]) );
  NOR2_X2A_A9TH \multiplier_1/U93  ( .A(\multiplier_1/n83 ), .B(
        \multiplier_1/n78 ), .Y(\multiplier_1/n61 ) );
  XOR2_X0P7M_A9TH \multiplier_1/U92  ( .A(\multiplier_1/n60 ), .B(
        \multiplier_1/n59 ), .Y(Result[2]) );
  NOR2_X1A_A9TH \multiplier_1/U91  ( .A(\multiplier_1/n78 ), .B(
        \multiplier_1/n77 ), .Y(\multiplier_1/n59 ) );
  INV_X0P8M_A9TH \multiplier_1/U90  ( .A(Result_add[2]), .Y(\multiplier_1/n55 ) );
  INV_X1M_A9TH \multiplier_1/U89  ( .A(\multiplier_1/n87 ), .Y(
        \multiplier_1/n45 ) );
  NAND2_X1P4M_A9TH \multiplier_1/U88  ( .A(\multiplier_1/n86 ), .B(
        \multiplier_1/n7 ), .Y(\multiplier_1/n60 ) );
  NOR2_X4M_A9TH \multiplier_1/U87  ( .A(\multiplier_1/n58 ), .B(
        \multiplier_1/n57 ), .Y(\multiplier_1/n77 ) );
  NAND2_X4M_A9TH \multiplier_1/U86  ( .A(\multiplier_1/n88 ), .B(
        \multiplier_1/n47 ), .Y(\multiplier_1/n29 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U85  ( .A(\multiplier_1/n90 ), .B(
        \multiplier_1/n26 ), .Y(Result[4]) );
  NOR2_X4M_A9TH \multiplier_1/U84  ( .A(\multiplier_1/n75 ), .B(
        \multiplier_1/n77 ), .Y(\multiplier_1/n83 ) );
  XNOR2_X4M_A9TH \multiplier_1/U83  ( .A(\multiplier_1/n54 ), .B(
        \multiplier_1/n21 ), .Y(\multiplier_1/n32 ) );
  INV_X2M_A9TH \multiplier_1/U82  ( .A(\multiplier_1/n43 ), .Y(
        \multiplier_1/n73 ) );
  NAND2_X1M_A9TH \multiplier_1/U81  ( .A(Result_add_2[2]), .B(Result_add[3]), 
        .Y(\multiplier_1/n72 ) );
  XOR2_X3M_A9TH \multiplier_1/U80  ( .A(\multiplier_1/n20 ), .B(
        \multiplier_1/n48 ), .Y(\multiplier_1/n88 ) );
  XNOR2_X3M_A9TH \multiplier_1/U79  ( .A(\multiplier_1/n34 ), .B(
        \multiplier_1/n17 ), .Y(\multiplier_1/n33 ) );
  INV_X0P8M_A9TH \multiplier_1/U78  ( .A(\multiplier_1/n17 ), .Y(
        \multiplier_1/n16 ) );
  NAND2_X1M_A9TH \multiplier_1/U77  ( .A(\multiplier_1/n23 ), .B(
        \multiplier_1/n13 ), .Y(\multiplier_1/n74 ) );
  NOR3_X4M_A9TH \multiplier_1/U76  ( .A(\multiplier_1/n54 ), .B(
        \multiplier_1/n55 ), .C(\multiplier_1/n62 ), .Y(\multiplier_1/n10 ) );
  INV_X2M_A9TH \multiplier_1/U75  ( .A(\multiplier_1/n22 ), .Y(
        \multiplier_1/n50 ) );
  INV_X2M_A9TH \multiplier_1/U74  ( .A(\multiplier_1/n8 ), .Y(
        \multiplier_1/n9 ) );
  INV_X2M_A9TH \multiplier_1/U73  ( .A(\multiplier_1/n77 ), .Y(
        \multiplier_1/n8 ) );
  NAND2_X6M_A9TH \multiplier_1/U72  ( .A(Result_add_2[1]), .B(Result_add[2]), 
        .Y(\multiplier_1/n11 ) );
  MXIT2_X0P5M_A9TH \multiplier_1/U71  ( .A(\multiplier_1/n89 ), .B(
        \multiplier_1/n88 ), .S0(\multiplier_1/n87 ), .Y(\multiplier_1/n90 )
         );
  XNOR2_X2M_A9TH \multiplier_1/U70  ( .A(\multiplier_1/n49 ), .B(
        \multiplier_1/n11 ), .Y(\multiplier_1/n87 ) );
  NAND2_X6M_A9TH \multiplier_1/U69  ( .A(Result_add[1]), .B(Result_add_2[2]), 
        .Y(\multiplier_1/n49 ) );
  NAND2_X4A_A9TH \multiplier_1/U68  ( .A(Result_add_2[1]), .B(Result_add[1]), 
        .Y(\multiplier_1/n54 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U67  ( .A(\multiplier_1/n82 ), .B(
        \multiplier_1/n8 ), .Y(\multiplier_1/n85 ) );
  INV_X1M_A9TH \multiplier_1/U66  ( .A(\multiplier_1/n25 ), .Y(
        \multiplier_1/n26 ) );
  AOI21_X0P7M_A9TH \multiplier_1/U65  ( .A0(\multiplier_1/n71 ), .A1(
        \multiplier_1/n72 ), .B0(\multiplier_1/n73 ), .Y(Result[6]) );
  NAND3_X3A_A9TH \multiplier_1/U64  ( .A(\multiplier_1/n12 ), .B(
        \multiplier_1/n43 ), .C(\multiplier_1/n87 ), .Y(\multiplier_1/n47 ) );
  NAND2_X1P4M_A9TH \multiplier_1/U63  ( .A(\multiplier_1/n28 ), .B(
        \multiplier_1/n27 ), .Y(\multiplier_1/n52 ) );
  INV_X1M_A9TH \multiplier_1/U62  ( .A(\multiplier_1/n41 ), .Y(
        \multiplier_1/n35 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U61  ( .A(\multiplier_1/n63 ), .B(
        \multiplier_1/n64 ), .Y(\multiplier_1/n79 ) );
  INV_X2M_A9TH \multiplier_1/U60  ( .A(\multiplier_1/n44 ), .Y(
        \multiplier_1/n23 ) );
  NAND2_X1M_A9TH \multiplier_1/U59  ( .A(Result_add[0]), .B(\multiplier_1/n6 ), 
        .Y(\multiplier_1/n66 ) );
  INV_X2M_A9TH \multiplier_1/U58  ( .A(Result_add_2[2]), .Y(\multiplier_1/n14 ) );
  NOR2_X4M_A9TH \multiplier_1/U57  ( .A(\multiplier_1/n19 ), .B(
        \multiplier_1/n14 ), .Y(\multiplier_1/n56 ) );
  NOR2_X4M_A9TH \multiplier_1/U56  ( .A(\multiplier_1/n53 ), .B(
        \multiplier_1/n19 ), .Y(\multiplier_1/n34 ) );
  NAND2_X1P4M_A9TH \multiplier_1/U55  ( .A(Result_add_2[1]), .B(Result_add[3]), 
        .Y(\multiplier_1/n41 ) );
  OAI21_X2M_A9TH \multiplier_1/U54  ( .A0(\multiplier_1/n32 ), .A1(
        \multiplier_1/n31 ), .B0(\multiplier_1/n30 ), .Y(\multiplier_1/n57 )
         );
  OAI21_X1M_A9TH \multiplier_1/U53  ( .A0(\multiplier_1/n5 ), .A1(
        \multiplier_1/n4 ), .B0(\multiplier_1/n48 ), .Y(\multiplier_1/n28 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U52  ( .A(\multiplier_1/n5 ), .B(
        \multiplier_1/n4 ), .Y(\multiplier_1/n27 ) );
  XOR2_X4M_A9TH \multiplier_1/U51  ( .A(\multiplier_1/n4 ), .B(
        \multiplier_1/n5 ), .Y(\multiplier_1/n20 ) );
  NAND2_X6A_A9TH \multiplier_1/U50  ( .A(Result_add_2[2]), .B(Result_add[2]), 
        .Y(\multiplier_1/n39 ) );
  XOR2_X4M_A9TH \multiplier_1/U49  ( .A(\multiplier_1/n38 ), .B(
        \multiplier_1/n39 ), .Y(\multiplier_1/n40 ) );
  XNOR2_X0P5M_A9TH \multiplier_1/U48  ( .A(\multiplier_1/n76 ), .B(
        \multiplier_1/n3 ), .Y(Result[3]) );
  NOR2_X8M_A9TH \multiplier_1/U47  ( .A(\multiplier_1/n49 ), .B(
        \multiplier_1/n11 ), .Y(\multiplier_1/n2 ) );
  NOR2_X1P4A_A9TH \multiplier_1/U46  ( .A(\multiplier_1/n2 ), .B(
        \multiplier_1/n56 ), .Y(\multiplier_1/n31 ) );
  NAND2_X1A_A9TH \multiplier_1/U45  ( .A(\multiplier_1/n7 ), .B(
        \multiplier_1/n1 ), .Y(\multiplier_1/n76 ) );
  INV_X1M_A9TH \multiplier_1/U44  ( .A(\multiplier_1/n71 ), .Y(
        \multiplier_1/n36 ) );
  INV_X1M_A9TH \multiplier_1/U43  ( .A(\multiplier_1/n72 ), .Y(
        \multiplier_1/n37 ) );
  NAND2_X3M_A9TH \multiplier_1/U42  ( .A(\multiplier_1/n40 ), .B(
        \multiplier_1/n35 ), .Y(\multiplier_1/n12 ) );
  AO21B_X1M_A9TH \multiplier_1/U41  ( .A0(\multiplier_1/n16 ), .A1(
        \multiplier_1/n34 ), .B0N(\multiplier_1/n15 ), .Y(\multiplier_1/n64 )
         );
  INV_X2M_A9TH \multiplier_1/U40  ( .A(\multiplier_1/n12 ), .Y(
        \multiplier_1/n44 ) );
  INV_X1P4M_A9TH \multiplier_1/U39  ( .A(\multiplier_1/n64 ), .Y(
        \multiplier_1/n65 ) );
  NAND2_X3M_A9TH \multiplier_1/U38  ( .A(\multiplier_1/n66 ), .B(
        \multiplier_1/n65 ), .Y(\multiplier_1/n82 ) );
  NAND2_X2M_A9TH \multiplier_1/U37  ( .A(\multiplier_1/n78 ), .B(
        \multiplier_1/n82 ), .Y(\multiplier_1/n80 ) );
  NAND2_X0P7A_A9TH \multiplier_1/U36  ( .A(\multiplier_1/n79 ), .B(
        \multiplier_1/n82 ), .Y(\multiplier_1/n67 ) );
  NAND2_X1P4M_A9TH \multiplier_1/U35  ( .A(\multiplier_1/n80 ), .B(
        \multiplier_1/n79 ), .Y(\multiplier_1/n81 ) );
  NOR2_X1A_A9TH \multiplier_1/U34  ( .A(\multiplier_1/n70 ), .B(
        \multiplier_1/n69 ), .Y(Result[7]) );
  INV_X0P7M_A9TH \multiplier_1/U33  ( .A(\multiplier_1/n66 ), .Y(
        \multiplier_1/n63 ) );
  XNOR2_X3M_A9TH \multiplier_1/U32  ( .A(\multiplier_1/n2 ), .B(
        \multiplier_1/n56 ), .Y(\multiplier_1/n18 ) );
  XOR2_X3M_A9TH \multiplier_1/U31  ( .A(\multiplier_1/n18 ), .B(
        \multiplier_1/n32 ), .Y(\multiplier_1/n22 ) );
  NAND2_X3A_A9TH \multiplier_1/U30  ( .A(\multiplier_1/n46 ), .B(
        \multiplier_1/n29 ), .Y(\multiplier_1/n3 ) );
  NAND2_X4M_A9TH \multiplier_1/U29  ( .A(\multiplier_1/n3 ), .B(
        \multiplier_1/n1 ), .Y(\multiplier_1/n86 ) );
  INV_X1M_A9TH \multiplier_1/U28  ( .A(Result_add[3]), .Y(\multiplier_1/n70 )
         );
  NAND2_X2A_A9TH \multiplier_1/U27  ( .A(\multiplier_1/n50 ), .B(
        \multiplier_1/n51 ), .Y(\multiplier_1/n1 ) );
  NAND2_X3M_A9TH \multiplier_1/U26  ( .A(\multiplier_1/n22 ), .B(
        \multiplier_1/n52 ), .Y(\multiplier_1/n75 ) );
  INV_X0P5B_A9TH \multiplier_1/U25  ( .A(Result_add_2[3]), .Y(
        \multiplier_1/n69 ) );
  NAND2_X4M_A9TH \multiplier_1/U24  ( .A(Result_add_2[0]), .B(Result_add[2]), 
        .Y(\multiplier_1/n21 ) );
  OAI21_X4M_A9TH \multiplier_1/U23  ( .A0(\multiplier_1/n86 ), .A1(
        \multiplier_1/n9 ), .B0(\multiplier_1/n61 ), .Y(\multiplier_1/n68 ) );
  AND2_X8M_A9TH \multiplier_1/U22  ( .A(Result_add_2[0]), .B(Result_add[3]), 
        .Y(\multiplier_1/n5 ) );
  INV_X2M_A9TH \multiplier_1/U21  ( .A(Result_add_2[0]), .Y(\multiplier_1/n62 ) );
  NAND2_X1M_A9TH \multiplier_1/U20  ( .A(\multiplier_1/n2 ), .B(
        \multiplier_1/n56 ), .Y(\multiplier_1/n30 ) );
  BUFH_X1P7M_A9TH \multiplier_1/U19  ( .A(\multiplier_1/n75 ), .Y(
        \multiplier_1/n7 ) );
  INV_X4M_A9TH \multiplier_1/U18  ( .A(Result_add_2[1]), .Y(\multiplier_1/n53 ) );
  NAND2_X8M_A9TH \multiplier_1/U17  ( .A(Result_add[1]), .B(Result_add_2[3]), 
        .Y(\multiplier_1/n38 ) );
  NAND2_X1M_A9TH \multiplier_1/U16  ( .A(Result_add[2]), .B(Result_add_2[3]), 
        .Y(\multiplier_1/n71 ) );
  INV_X3M_A9TH \multiplier_1/U15  ( .A(Result_add[0]), .Y(\multiplier_1/n19 )
         );
  NAND2_X1A_A9TH \multiplier_1/U14  ( .A(\multiplier_1/n37 ), .B(
        \multiplier_1/n36 ), .Y(\multiplier_1/n43 ) );
  INV_X2M_A9TH \multiplier_1/U13  ( .A(\multiplier_1/n40 ), .Y(
        \multiplier_1/n42 ) );
  NAND2_X3A_A9TH \multiplier_1/U12  ( .A(Result_add_2[0]), .B(Result_add[1]), 
        .Y(\multiplier_1/n17 ) );
  NAND2_X4M_A9TH \multiplier_1/U11  ( .A(\multiplier_1/n42 ), .B(
        \multiplier_1/n41 ), .Y(\multiplier_1/n13 ) );
  NOR2_X1A_A9TH \multiplier_1/U10  ( .A(\multiplier_1/n19 ), .B(
        \multiplier_1/n69 ), .Y(\multiplier_1/n48 ) );
  NOR2_X4M_A9TH \multiplier_1/U9  ( .A(\multiplier_1/n38 ), .B(
        \multiplier_1/n39 ), .Y(\multiplier_1/n4 ) );
  OAI2XB1_X1M_A9TH \multiplier_1/U8  ( .A1N(\multiplier_1/n17 ), .A0(
        \multiplier_1/n34 ), .B0(\multiplier_1/n10 ), .Y(\multiplier_1/n15 )
         );
  NAND2_X4M_A9TH \multiplier_1/U7  ( .A(\multiplier_1/n13 ), .B(
        \multiplier_1/n73 ), .Y(\multiplier_1/n24 ) );
  INV_X0P6M_A9TH \multiplier_1/U6  ( .A(\multiplier_1/n62 ), .Y(
        \multiplier_1/n6 ) );
  NAND2_X4M_A9TH \multiplier_1/U5  ( .A(\multiplier_1/n23 ), .B(
        \multiplier_1/n24 ), .Y(\multiplier_1/n25 ) );
  XOR2_X3M_A9TH \multiplier_1/U4  ( .A(\multiplier_1/n33 ), .B(
        \multiplier_1/n10 ), .Y(\multiplier_1/n58 ) );
  NAND2_X2M_A9TH \multiplier_1/U3  ( .A(\multiplier_1/n25 ), .B(
        \multiplier_1/n45 ), .Y(\multiplier_1/n46 ) );
  INV_X1M_A9TH \multiplier_1/U2  ( .A(\multiplier_1/n52 ), .Y(
        \multiplier_1/n51 ) );
  AND2_X3M_A9TH \multiplier_1/U1  ( .A(\multiplier_1/n58 ), .B(
        \multiplier_1/n57 ), .Y(\multiplier_1/n78 ) );
endmodule

