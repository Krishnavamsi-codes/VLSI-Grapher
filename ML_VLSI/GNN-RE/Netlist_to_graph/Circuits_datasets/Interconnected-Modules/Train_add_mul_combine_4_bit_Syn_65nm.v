/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : O-2018.06-SP5-5
// Date      : Sat Sep 26 09:25:03 2020
/////////////////////////////////////////////////////////////


module add_mul_combine_4_bit ( a, b, Result_mul, Result_add );
  input [0:3] a;
  input [0:3] b;
  output [0:7] Result_mul;
  output [0:3] Result_add;
  wire   \adder_1/n4 , \adder_1/n3 , \adder_1/n2 , \adder_1/n1 ,
         \multiplier_1/n59 , \multiplier_1/n58 , \multiplier_1/n57 ,
         \multiplier_1/n56 , \multiplier_1/n55 , \multiplier_1/n54 ,
         \multiplier_1/n53 , \multiplier_1/n52 , \multiplier_1/n51 ,
         \multiplier_1/n50 , \multiplier_1/n49 , \multiplier_1/n48 ,
         \multiplier_1/n47 , \multiplier_1/n46 , \multiplier_1/n45 ,
         \multiplier_1/n44 , \multiplier_1/n43 , \multiplier_1/n42 ,
         \multiplier_1/n41 , \multiplier_1/n40 , \multiplier_1/n39 ,
         \multiplier_1/n38 , \multiplier_1/n37 , \multiplier_1/n36 ,
         \multiplier_1/n35 , \multiplier_1/n34 , \multiplier_1/n33 ,
         \multiplier_1/n32 , \multiplier_1/n31 , \multiplier_1/n30 ,
         \multiplier_1/n29 , \multiplier_1/n28 , \multiplier_1/n27 ,
         \multiplier_1/n26 , \multiplier_1/n25 , \multiplier_1/n24 ,
         \multiplier_1/n23 , \multiplier_1/n22 , \multiplier_1/n21 ,
         \multiplier_1/n20 , \multiplier_1/n19 , \multiplier_1/n18 ,
         \multiplier_1/n17 , \multiplier_1/n16 , \multiplier_1/n15 ,
         \multiplier_1/n14 , \multiplier_1/n13 , \multiplier_1/n12 ,
         \multiplier_1/n11 , \multiplier_1/n10 , \multiplier_1/n9 ,
         \multiplier_1/n8 , \multiplier_1/n7 , \multiplier_1/n6 ,
         \multiplier_1/n5 , \multiplier_1/n4 , \multiplier_1/n3 ,
         \multiplier_1/n2 , \multiplier_1/n1 ;

  ADDF_X1M_A9TH \adder_1/U6  ( .A(b[1]), .B(a[1]), .CI(\adder_1/n4 ), .CO(
        \adder_1/n1 ), .S(Result_add[1]) );
  ADDF_X1M_A9TH \adder_1/U5  ( .A(b[2]), .B(a[2]), .CI(\adder_1/n3 ), .CO(
        \adder_1/n4 ), .S(Result_add[2]) );
  NOR2_X0P5M_A9TH \adder_1/U4  ( .A(\adder_1/n2 ), .B(\adder_1/n3 ), .Y(
        Result_add[3]) );
  XOR3_X0P5M_A9TH \adder_1/U3  ( .A(\adder_1/n1 ), .B(b[0]), .C(a[0]), .Y(
        Result_add[0]) );
  NOR2_X0P5M_A9TH \adder_1/U2  ( .A(a[3]), .B(b[3]), .Y(\adder_1/n2 ) );
  AND2_X0P5M_A9TH \adder_1/U1  ( .A(a[3]), .B(b[3]), .Y(\adder_1/n3 ) );
  AND2_X0P5M_A9TH \multiplier_1/U61  ( .A(\multiplier_1/n59 ), .B(
        \multiplier_1/n58 ), .Y(Result_mul[6]) );
  OR2_X0P5M_A9TH \multiplier_1/U60  ( .A(\multiplier_1/n57 ), .B(
        \multiplier_1/n56 ), .Y(\multiplier_1/n59 ) );
  AO21_X0P5M_A9TH \multiplier_1/U59  ( .A0(\multiplier_1/n55 ), .A1(
        \multiplier_1/n54 ), .B0(\multiplier_1/n51 ), .Y(Result_mul[0]) );
  XNOR2_X0P5M_A9TH \multiplier_1/U58  ( .A(\multiplier_1/n55 ), .B(
        \multiplier_1/n52 ), .Y(Result_mul[1]) );
  INV_X0P5B_A9TH \multiplier_1/U57  ( .A(\multiplier_1/n51 ), .Y(
        \multiplier_1/n53 ) );
  ADDF_X1M_A9TH \multiplier_1/U56  ( .A(\multiplier_1/n50 ), .B(
        \multiplier_1/n49 ), .CI(\multiplier_1/n48 ), .CO(\multiplier_1/n51 ), 
        .S(\multiplier_1/n40 ) );
  OAI21_X1M_A9TH \multiplier_1/U55  ( .A0(\multiplier_1/n45 ), .A1(
        \multiplier_1/n44 ), .B0(\multiplier_1/n43 ), .Y(\multiplier_1/n55 )
         );
  XOR2_X0P5M_A9TH \multiplier_1/U54  ( .A(\multiplier_1/n45 ), .B(
        \multiplier_1/n42 ), .Y(Result_mul[2]) );
  NAND2_X1M_A9TH \multiplier_1/U53  ( .A(\multiplier_1/n40 ), .B(
        \multiplier_1/n39 ), .Y(\multiplier_1/n43 ) );
  ADDF_X1M_A9TH \multiplier_1/U52  ( .A(\multiplier_1/n38 ), .B(
        \multiplier_1/n37 ), .CI(\multiplier_1/n36 ), .CO(\multiplier_1/n39 ), 
        .S(\multiplier_1/n24 ) );
  ADDH_X1M_A9TH \multiplier_1/U51  ( .A(\multiplier_1/n35 ), .B(
        \multiplier_1/n34 ), .CO(\multiplier_1/n48 ), .S(\multiplier_1/n36 )
         );
  NOR2_X1A_A9TH \multiplier_1/U50  ( .A(\multiplier_1/n33 ), .B(
        \multiplier_1/n46 ), .Y(\multiplier_1/n49 ) );
  NOR2_X1A_A9TH \multiplier_1/U49  ( .A(\multiplier_1/n47 ), .B(
        \multiplier_1/n32 ), .Y(\multiplier_1/n50 ) );
  AOI21_X1M_A9TH \multiplier_1/U48  ( .A0(\multiplier_1/n31 ), .A1(
        \multiplier_1/n1 ), .B0(\multiplier_1/n30 ), .Y(\multiplier_1/n45 ) );
  XNOR2_X0P5M_A9TH \multiplier_1/U47  ( .A(\multiplier_1/n28 ), .B(
        \multiplier_1/n31 ), .Y(Result_mul[3]) );
  ADDF_X1M_A9TH \multiplier_1/U46  ( .A(\multiplier_1/n22 ), .B(
        \multiplier_1/n21 ), .CI(\multiplier_1/n20 ), .CO(\multiplier_1/n23 ), 
        .S(\multiplier_1/n11 ) );
  ADDH_X1M_A9TH \multiplier_1/U45  ( .A(\multiplier_1/n17 ), .B(
        \multiplier_1/n16 ), .CO(\multiplier_1/n37 ), .S(\multiplier_1/n10 )
         );
  NOR2_X1A_A9TH \multiplier_1/U44  ( .A(\multiplier_1/n33 ), .B(
        \multiplier_1/n32 ), .Y(\multiplier_1/n38 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U43  ( .A(\multiplier_1/n15 ), .B(
        \multiplier_1/n26 ), .Y(Result_mul[4]) );
  ADDH_X1M_A9TH \multiplier_1/U42  ( .A(\multiplier_1/n8 ), .B(
        \multiplier_1/n7 ), .CO(\multiplier_1/n20 ), .S(\multiplier_1/n3 ) );
  NOR2_X1A_A9TH \multiplier_1/U41  ( .A(\multiplier_1/n33 ), .B(
        \multiplier_1/n19 ), .Y(\multiplier_1/n21 ) );
  NOR2_X1A_A9TH \multiplier_1/U40  ( .A(\multiplier_1/n47 ), .B(
        \multiplier_1/n6 ), .Y(\multiplier_1/n22 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U39  ( .A(\multiplier_1/n5 ), .B(
        \multiplier_1/n58 ), .Y(Result_mul[5]) );
  NOR2_X1A_A9TH \multiplier_1/U38  ( .A(\multiplier_1/n33 ), .B(
        \multiplier_1/n6 ), .Y(\multiplier_1/n7 ) );
  NOR2_X1A_A9TH \multiplier_1/U37  ( .A(\multiplier_1/n18 ), .B(
        \multiplier_1/n19 ), .Y(\multiplier_1/n8 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U36  ( .A(\multiplier_1/n9 ), .B(
        \multiplier_1/n6 ), .Y(Result_mul[7]) );
  INV_X0P5B_A9TH \multiplier_1/U35  ( .A(\multiplier_1/n14 ), .Y(
        \multiplier_1/n4 ) );
  OR2_X0P5M_A9TH \multiplier_1/U34  ( .A(\multiplier_1/n24 ), .B(
        \multiplier_1/n23 ), .Y(\multiplier_1/n1 ) );
  INV_X0P5B_A9TH \multiplier_1/U33  ( .A(\multiplier_1/n44 ), .Y(
        \multiplier_1/n41 ) );
  INV_X0P5B_A9TH \multiplier_1/U32  ( .A(\multiplier_1/n27 ), .Y(
        \multiplier_1/n12 ) );
  INV_X0P5B_A9TH \multiplier_1/U31  ( .A(\multiplier_1/n29 ), .Y(
        \multiplier_1/n30 ) );
  INV_X1M_A9TH \multiplier_1/U30  ( .A(a[0]), .Y(\multiplier_1/n46 ) );
  NOR2_X1A_A9TH \multiplier_1/U29  ( .A(\multiplier_1/n18 ), .B(
        \multiplier_1/n46 ), .Y(\multiplier_1/n35 ) );
  NOR2_X1A_A9TH \multiplier_1/U28  ( .A(\multiplier_1/n47 ), .B(
        \multiplier_1/n19 ), .Y(\multiplier_1/n34 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U27  ( .A(\multiplier_1/n57 ), .B(
        \multiplier_1/n56 ), .Y(\multiplier_1/n58 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U26  ( .A(\multiplier_1/n3 ), .B(
        \multiplier_1/n2 ), .Y(\multiplier_1/n13 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U25  ( .A(\multiplier_1/n11 ), .B(
        \multiplier_1/n10 ), .Y(\multiplier_1/n25 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U24  ( .A(\multiplier_1/n24 ), .B(
        \multiplier_1/n23 ), .Y(\multiplier_1/n29 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U23  ( .A(\multiplier_1/n40 ), .B(
        \multiplier_1/n39 ), .Y(\multiplier_1/n44 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U22  ( .A(\multiplier_1/n1 ), .B(
        \multiplier_1/n29 ), .Y(\multiplier_1/n28 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U21  ( .A(\multiplier_1/n12 ), .B(
        \multiplier_1/n25 ), .Y(\multiplier_1/n15 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U20  ( .A(\multiplier_1/n47 ), .B(
        \multiplier_1/n46 ), .Y(\multiplier_1/n54 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U19  ( .A(\multiplier_1/n18 ), .B(
        \multiplier_1/n6 ), .Y(\multiplier_1/n57 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U18  ( .A(\multiplier_1/n9 ), .B(
        \multiplier_1/n32 ), .Y(\multiplier_1/n2 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U17  ( .A(\multiplier_1/n3 ), .B(
        \multiplier_1/n2 ), .Y(\multiplier_1/n14 ) );
  OA21_X0P5M_A9TH \multiplier_1/U16  ( .A0(\multiplier_1/n14 ), .A1(
        \multiplier_1/n58 ), .B0(\multiplier_1/n13 ), .Y(\multiplier_1/n26 )
         );
  INV_X0P8M_A9TH \multiplier_1/U15  ( .A(a[3]), .Y(\multiplier_1/n6 ) );
  INV_X0P8M_A9TH \multiplier_1/U14  ( .A(b[3]), .Y(\multiplier_1/n9 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U13  ( .A(\multiplier_1/n9 ), .B(
        \multiplier_1/n46 ), .Y(\multiplier_1/n17 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U12  ( .A(\multiplier_1/n54 ), .B(
        \multiplier_1/n53 ), .Y(\multiplier_1/n52 ) );
  OAI21_X0P7M_A9TH \multiplier_1/U11  ( .A0(\multiplier_1/n27 ), .A1(
        \multiplier_1/n26 ), .B0(\multiplier_1/n25 ), .Y(\multiplier_1/n31 )
         );
  NAND2_X0P5M_A9TH \multiplier_1/U10  ( .A(\multiplier_1/n4 ), .B(
        \multiplier_1/n13 ), .Y(\multiplier_1/n5 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U9  ( .A(\multiplier_1/n41 ), .B(
        \multiplier_1/n43 ), .Y(\multiplier_1/n42 ) );
  INV_X1M_A9TH \multiplier_1/U8  ( .A(a[1]), .Y(\multiplier_1/n32 ) );
  INV_X1M_A9TH \multiplier_1/U7  ( .A(b[1]), .Y(\multiplier_1/n33 ) );
  INV_X1M_A9TH \multiplier_1/U6  ( .A(b[0]), .Y(\multiplier_1/n47 ) );
  INV_X1M_A9TH \multiplier_1/U5  ( .A(b[2]), .Y(\multiplier_1/n18 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U4  ( .A(\multiplier_1/n18 ), .B(
        \multiplier_1/n32 ), .Y(\multiplier_1/n16 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U3  ( .A(\multiplier_1/n9 ), .B(
        \multiplier_1/n19 ), .Y(\multiplier_1/n56 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U2  ( .A(\multiplier_1/n11 ), .B(
        \multiplier_1/n10 ), .Y(\multiplier_1/n27 ) );
  INV_X1M_A9TH \multiplier_1/U1  ( .A(a[2]), .Y(\multiplier_1/n19 ) );
endmodule

