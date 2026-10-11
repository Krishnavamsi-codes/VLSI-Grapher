/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : O-2018.06-SP5-5
// Date      : Sat Sep 26 22:54:19 2020
/////////////////////////////////////////////////////////////


module add_mul_comp_4_bit ( a, b, Result );
  input [0:3] a;
  input [0:3] b;
  output [0:7] Result;
  wire   A_greater_B, n1, \adder_1/n4 , \adder_1/n3 , \adder_1/n2 ,
         \adder_1/n1 , \multiplier_1/n63 , \multiplier_1/n62 ,
         \multiplier_1/n61 , \multiplier_1/n60 , \multiplier_1/n59 ,
         \multiplier_1/n58 , \multiplier_1/n57 , \multiplier_1/n56 ,
         \multiplier_1/n55 , \multiplier_1/n54 , \multiplier_1/n53 ,
         \multiplier_1/n52 , \multiplier_1/n51 , \multiplier_1/n50 ,
         \multiplier_1/n49 , \multiplier_1/n48 , \multiplier_1/n47 ,
         \multiplier_1/n46 , \multiplier_1/n45 , \multiplier_1/n44 ,
         \multiplier_1/n43 , \multiplier_1/n42 , \multiplier_1/n41 ,
         \multiplier_1/n40 , \multiplier_1/n39 , \multiplier_1/n38 ,
         \multiplier_1/n37 , \multiplier_1/n36 , \multiplier_1/n35 ,
         \multiplier_1/n34 , \multiplier_1/n33 , \multiplier_1/n32 ,
         \multiplier_1/n31 , \multiplier_1/n30 , \multiplier_1/n29 ,
         \multiplier_1/n28 , \multiplier_1/n27 , \multiplier_1/n26 ,
         \multiplier_1/n25 , \multiplier_1/n24 , \multiplier_1/n23 ,
         \multiplier_1/n22 , \multiplier_1/n21 , \multiplier_1/n20 ,
         \multiplier_1/n19 , \multiplier_1/n18 , \multiplier_1/n17 ,
         \multiplier_1/n16 , \multiplier_1/n15 , \multiplier_1/n14 ,
         \multiplier_1/n13 , \multiplier_1/n12 , \multiplier_1/n11 ,
         \multiplier_1/n10 , \multiplier_1/n9 , \multiplier_1/n8 ,
         \multiplier_1/n7 , \multiplier_1/n6 , \multiplier_1/n5 ,
         \multiplier_1/n4 , \multiplier_1/n3 , \multiplier_1/n2 ,
         \multiplier_1/n1 , \comparator_1/n6 , \comparator_1/n5 ,
         \comparator_1/n4 , \comparator_1/n3 , \comparator_1/n2 ,
         \comparator_1/n1 ;
  wire   [0:7] Result_add;
  wire   [0:7] Result_mul;

  BUF_X1M_A9TH U9 ( .A(A_greater_B), .Y(n1) );
  AND2_X0P5M_A9TH U10 ( .A(n1), .B(Result_mul[2]), .Y(Result[2]) );
  AND2_X0P5M_A9TH U11 ( .A(n1), .B(Result_mul[1]), .Y(Result[1]) );
  MXT2_X0P5M_A9TH U12 ( .A(Result_add[6]), .B(Result_mul[6]), .S0(n1), .Y(
        Result[6]) );
  MXT2_X0P5M_A9TH U13 ( .A(Result_add[5]), .B(Result_mul[5]), .S0(n1), .Y(
        Result[5]) );
  MXT2_X0P5M_A9TH U14 ( .A(Result_add[7]), .B(Result_mul[7]), .S0(n1), .Y(
        Result[7]) );
  MXT2_X0P5M_A9TH U15 ( .A(Result_add[4]), .B(Result_mul[4]), .S0(n1), .Y(
        Result[4]) );
  AND2_X0P5M_A9TH U16 ( .A(n1), .B(Result_mul[3]), .Y(Result[3]) );
  AND2_X0P5M_A9TH U17 ( .A(n1), .B(Result_mul[0]), .Y(Result[0]) );
  ADDF_X1M_A9TH \adder_1/U7  ( .A(b[1]), .B(a[1]), .CI(\adder_1/n4 ), .CO(
        \adder_1/n1 ), .S(Result_add[5]) );
  ADDF_X1M_A9TH \adder_1/U6  ( .A(b[2]), .B(a[2]), .CI(\adder_1/n3 ), .CO(
        \adder_1/n4 ), .S(Result_add[6]) );
  XOR3_X0P5M_A9TH \adder_1/U5  ( .A(\adder_1/n1 ), .B(b[0]), .C(a[0]), .Y(
        Result_add[4]) );
  AND2_X0P7M_A9TH \adder_1/U4  ( .A(a[3]), .B(b[3]), .Y(\adder_1/n3 ) );
  NOR2_X0P7A_A9TH \adder_1/U3  ( .A(\adder_1/n2 ), .B(\adder_1/n3 ), .Y(
        Result_add[7]) );
  NOR2_X0P5M_A9TH \adder_1/U2  ( .A(a[3]), .B(b[3]), .Y(\adder_1/n2 ) );
  INV_X0P5B_A9TH \multiplier_1/U65  ( .A(\multiplier_1/n57 ), .Y(
        \multiplier_1/n59 ) );
  INV_X0P5B_A9TH \multiplier_1/U64  ( .A(\multiplier_1/n52 ), .Y(
        \multiplier_1/n54 ) );
  OR2_X0P5M_A9TH \multiplier_1/U63  ( .A(\multiplier_1/n50 ), .B(
        \multiplier_1/n49 ), .Y(\multiplier_1/n51 ) );
  XOR2_X0P7M_A9TH \multiplier_1/U62  ( .A(\multiplier_1/n48 ), .B(
        \multiplier_1/n47 ), .Y(Result_mul[1]) );
  INV_X0P5B_A9TH \multiplier_1/U61  ( .A(\multiplier_1/n40 ), .Y(
        \multiplier_1/n42 ) );
  OAI21_X1M_A9TH \multiplier_1/U60  ( .A0(\multiplier_1/n39 ), .A1(
        \multiplier_1/n38 ), .B0(\multiplier_1/n37 ), .Y(\multiplier_1/n44 )
         );
  INV_X0P5B_A9TH \multiplier_1/U59  ( .A(\multiplier_1/n38 ), .Y(
        \multiplier_1/n34 ) );
  ADDF_X1M_A9TH \multiplier_1/U58  ( .A(\multiplier_1/n32 ), .B(
        \multiplier_1/n31 ), .CI(\multiplier_1/n30 ), .CO(\multiplier_1/n33 ), 
        .S(\multiplier_1/n24 ) );
  INV_X0P5B_A9TH \multiplier_1/U57  ( .A(\multiplier_1/n29 ), .Y(
        \multiplier_1/n45 ) );
  AOI21_X1M_A9TH \multiplier_1/U56  ( .A0(\multiplier_1/n26 ), .A1(
        \multiplier_1/n35 ), .B0(\multiplier_1/n25 ), .Y(\multiplier_1/n48 )
         );
  NAND2_X1M_A9TH \multiplier_1/U55  ( .A(\multiplier_1/n22 ), .B(
        \multiplier_1/n21 ), .Y(\multiplier_1/n37 ) );
  OAI21_X1M_A9TH \multiplier_1/U54  ( .A0(\multiplier_1/n52 ), .A1(
        \multiplier_1/n55 ), .B0(\multiplier_1/n53 ), .Y(\multiplier_1/n35 )
         );
  ADDH_X1M_A9TH \multiplier_1/U53  ( .A(\multiplier_1/n13 ), .B(
        \multiplier_1/n12 ), .CO(\multiplier_1/n7 ), .S(\multiplier_1/n18 ) );
  NOR2_X1A_A9TH \multiplier_1/U52  ( .A(\multiplier_1/n20 ), .B(
        \multiplier_1/n19 ), .Y(\multiplier_1/n52 ) );
  ADDH_X1M_A9TH \multiplier_1/U51  ( .A(\multiplier_1/n11 ), .B(
        \multiplier_1/n10 ), .CO(\multiplier_1/n5 ), .S(\multiplier_1/n19 ) );
  ADDF_X1M_A9TH \multiplier_1/U50  ( .A(\multiplier_1/n9 ), .B(
        \multiplier_1/n8 ), .CI(\multiplier_1/n7 ), .CO(\multiplier_1/n21 ), 
        .S(\multiplier_1/n20 ) );
  NOR2_X1A_A9TH \multiplier_1/U49  ( .A(\multiplier_1/n24 ), .B(
        \multiplier_1/n23 ), .Y(\multiplier_1/n40 ) );
  ADDF_X1M_A9TH \multiplier_1/U48  ( .A(\multiplier_1/n6 ), .B(
        \multiplier_1/n5 ), .CI(\multiplier_1/n4 ), .CO(\multiplier_1/n23 ), 
        .S(\multiplier_1/n22 ) );
  ADDH_X1M_A9TH \multiplier_1/U47  ( .A(\multiplier_1/n3 ), .B(
        \multiplier_1/n2 ), .CO(\multiplier_1/n30 ), .S(\multiplier_1/n4 ) );
  NOR2_X1A_A9TH \multiplier_1/U46  ( .A(\multiplier_1/n1 ), .B(
        \multiplier_1/n27 ), .Y(\multiplier_1/n31 ) );
  NOR2_X1A_A9TH \multiplier_1/U45  ( .A(\multiplier_1/n28 ), .B(
        \multiplier_1/n14 ), .Y(\multiplier_1/n32 ) );
  NOR2_X1A_A9TH \multiplier_1/U44  ( .A(\multiplier_1/n22 ), .B(
        \multiplier_1/n21 ), .Y(\multiplier_1/n38 ) );
  NOR2_X1A_A9TH \multiplier_1/U43  ( .A(\multiplier_1/n1 ), .B(
        \multiplier_1/n16 ), .Y(\multiplier_1/n8 ) );
  NOR2_X1A_A9TH \multiplier_1/U42  ( .A(\multiplier_1/n28 ), .B(
        \multiplier_1/n62 ), .Y(\multiplier_1/n9 ) );
  NOR2_X1A_A9TH \multiplier_1/U41  ( .A(\multiplier_1/n28 ), .B(
        \multiplier_1/n16 ), .Y(\multiplier_1/n2 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U40  ( .A(\multiplier_1/n36 ), .B(
        \multiplier_1/n39 ), .Y(Result_mul[3]) );
  XOR2_X0P5M_A9TH \multiplier_1/U39  ( .A(\multiplier_1/n56 ), .B(
        \multiplier_1/n55 ), .Y(Result_mul[4]) );
  XOR2_X0P5M_A9TH \multiplier_1/U38  ( .A(\multiplier_1/n61 ), .B(
        \multiplier_1/n60 ), .Y(Result_mul[5]) );
  NOR2_X0P7A_A9TH \multiplier_1/U37  ( .A(\multiplier_1/n1 ), .B(
        \multiplier_1/n14 ), .Y(\multiplier_1/n6 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U36  ( .A(\multiplier_1/n63 ), .B(
        \multiplier_1/n27 ), .Y(\multiplier_1/n11 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U35  ( .A(\multiplier_1/n1 ), .B(
        \multiplier_1/n62 ), .Y(\multiplier_1/n12 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U34  ( .A(\multiplier_1/n15 ), .B(
        \multiplier_1/n27 ), .Y(\multiplier_1/n3 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U33  ( .A(\multiplier_1/n15 ), .B(
        \multiplier_1/n14 ), .Y(\multiplier_1/n10 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U32  ( .A(\multiplier_1/n15 ), .B(
        \multiplier_1/n62 ), .Y(\multiplier_1/n50 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U31  ( .A(\multiplier_1/n63 ), .B(
        \multiplier_1/n16 ), .Y(\multiplier_1/n49 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U30  ( .A(\multiplier_1/n15 ), .B(
        \multiplier_1/n16 ), .Y(\multiplier_1/n13 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U29  ( .A(\multiplier_1/n50 ), .B(
        \multiplier_1/n49 ), .Y(\multiplier_1/n60 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U28  ( .A(\multiplier_1/n18 ), .B(
        \multiplier_1/n17 ), .Y(\multiplier_1/n58 ) );
  OA21_X0P7M_A9TH \multiplier_1/U27  ( .A0(\multiplier_1/n57 ), .A1(
        \multiplier_1/n60 ), .B0(\multiplier_1/n58 ), .Y(\multiplier_1/n55 )
         );
  NAND2_X0P7M_A9TH \multiplier_1/U26  ( .A(\multiplier_1/n24 ), .B(
        \multiplier_1/n23 ), .Y(\multiplier_1/n41 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U25  ( .A(\multiplier_1/n59 ), .B(
        \multiplier_1/n58 ), .Y(\multiplier_1/n61 ) );
  OAI21_X0P7M_A9TH \multiplier_1/U24  ( .A0(\multiplier_1/n37 ), .A1(
        \multiplier_1/n40 ), .B0(\multiplier_1/n41 ), .Y(\multiplier_1/n25 )
         );
  NAND2_X0P7M_A9TH \multiplier_1/U23  ( .A(\multiplier_1/n54 ), .B(
        \multiplier_1/n53 ), .Y(\multiplier_1/n56 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U22  ( .A(\multiplier_1/n34 ), .B(
        \multiplier_1/n37 ), .Y(\multiplier_1/n36 ) );
  OAI21_X0P7M_A9TH \multiplier_1/U21  ( .A0(\multiplier_1/n48 ), .A1(
        \multiplier_1/n45 ), .B0(\multiplier_1/n46 ), .Y(Result_mul[0]) );
  XNOR2_X0P5M_A9TH \multiplier_1/U20  ( .A(\multiplier_1/n44 ), .B(
        \multiplier_1/n43 ), .Y(Result_mul[2]) );
  INV_X0P7M_A9TH \multiplier_1/U19  ( .A(a[3]), .Y(\multiplier_1/n62 ) );
  INV_X0P7M_A9TH \multiplier_1/U18  ( .A(b[3]), .Y(\multiplier_1/n63 ) );
  INV_X0P7M_A9TH \multiplier_1/U17  ( .A(a[0]), .Y(\multiplier_1/n27 ) );
  INV_X0P7M_A9TH \multiplier_1/U16  ( .A(b[1]), .Y(\multiplier_1/n1 ) );
  INV_X0P7M_A9TH \multiplier_1/U15  ( .A(a[2]), .Y(\multiplier_1/n16 ) );
  INV_X0P7M_A9TH \multiplier_1/U14  ( .A(b[2]), .Y(\multiplier_1/n15 ) );
  INV_X0P7M_A9TH \multiplier_1/U13  ( .A(a[1]), .Y(\multiplier_1/n14 ) );
  INV_X0P7M_A9TH \multiplier_1/U12  ( .A(b[0]), .Y(\multiplier_1/n28 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U11  ( .A(\multiplier_1/n28 ), .B(
        \multiplier_1/n27 ), .Y(\multiplier_1/n29 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U10  ( .A(\multiplier_1/n63 ), .B(
        \multiplier_1/n62 ), .Y(Result_mul[7]) );
  NOR2_X0P5M_A9TH \multiplier_1/U9  ( .A(\multiplier_1/n63 ), .B(
        \multiplier_1/n14 ), .Y(\multiplier_1/n17 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U8  ( .A(\multiplier_1/n18 ), .B(
        \multiplier_1/n17 ), .Y(\multiplier_1/n57 ) );
  AND2_X0P5M_A9TH \multiplier_1/U7  ( .A(\multiplier_1/n51 ), .B(
        \multiplier_1/n60 ), .Y(Result_mul[6]) );
  INV_X0P6M_A9TH \multiplier_1/U6  ( .A(\multiplier_1/n33 ), .Y(
        \multiplier_1/n46 ) );
  NAND2_X1M_A9TH \multiplier_1/U5  ( .A(\multiplier_1/n20 ), .B(
        \multiplier_1/n19 ), .Y(\multiplier_1/n53 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U4  ( .A(\multiplier_1/n38 ), .B(
        \multiplier_1/n40 ), .Y(\multiplier_1/n26 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U3  ( .A(\multiplier_1/n29 ), .B(
        \multiplier_1/n46 ), .Y(\multiplier_1/n47 ) );
  INV_X0P6M_A9TH \multiplier_1/U2  ( .A(\multiplier_1/n35 ), .Y(
        \multiplier_1/n39 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U1  ( .A(\multiplier_1/n42 ), .B(
        \multiplier_1/n41 ), .Y(\multiplier_1/n43 ) );
  OAI21_X1M_A9TH \comparator_1/U7  ( .A0(a[1]), .A1(\comparator_1/n4 ), .B0(
        \comparator_1/n3 ), .Y(\comparator_1/n5 ) );
  INV_X0P5B_A9TH \comparator_1/U6  ( .A(a[2]), .Y(\comparator_1/n1 ) );
  AOI222_X1M_A9TH \comparator_1/U5  ( .A0(b[0]), .A1(\comparator_1/n6 ), .B0(
        b[0]), .B1(\comparator_1/n5 ), .C0(\comparator_1/n6 ), .C1(
        \comparator_1/n5 ), .Y(A_greater_B) );
  OAI22_X0P7M_A9TH \comparator_1/U4  ( .A0(b[3]), .A1(\comparator_1/n2 ), .B0(
        \comparator_1/n1 ), .B1(b[2]), .Y(\comparator_1/n4 ) );
  INV_X0P7M_A9TH \comparator_1/U3  ( .A(a[0]), .Y(\comparator_1/n6 ) );
  AO21B_X0P5M_A9TH \comparator_1/U2  ( .A0(b[2]), .A1(\comparator_1/n1 ), 
        .B0N(a[3]), .Y(\comparator_1/n2 ) );
  AO21B_X1M_A9TH \comparator_1/U1  ( .A0(a[1]), .A1(\comparator_1/n4 ), .B0N(
        b[1]), .Y(\comparator_1/n3 ) );
endmodule

