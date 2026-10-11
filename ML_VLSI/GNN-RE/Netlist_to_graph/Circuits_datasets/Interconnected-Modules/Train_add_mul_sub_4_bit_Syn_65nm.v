/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : O-2018.06-SP5-5
// Date      : Sun Sep 27 00:01:14 2020
/////////////////////////////////////////////////////////////


module add_mul_sub_4_bit ( a, b, operation, Result );
  input [0:3] a;
  input [0:3] b;
  input [0:1] operation;
  output [0:7] Result;
  wire   n27, n28, n29, n30, n31, n32, n33, n34, n35, n36, n37, n38, n39, n40,
         n41, n42, \subtractor_1/n1 , \subtractor_1/intadd_0/n1 ,
         \subtractor_1/intadd_0/n2 , \subtractor_1/intadd_0/n3 ,
         \subtractor_1/intadd_0/CI , \subtractor_1/intadd_0/B[0] ,
         \subtractor_1/intadd_0/B[1] , \subtractor_1/intadd_0/B[2] ,
         \subtractor_2/n1 , \subtractor_2/intadd_1/n1 ,
         \subtractor_2/intadd_1/n2 , \subtractor_2/intadd_1/n3 ,
         \subtractor_2/intadd_1/CI , \subtractor_2/intadd_1/B[0] ,
         \subtractor_2/intadd_1/B[1] , \subtractor_2/intadd_1/B[2] ,
         \adder_1/n4 , \adder_1/n3 , \adder_1/n2 , \adder_1/n1 ,
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
  wire   [0:7] Result_sub1;
  wire   [0:7] Result_sub2;
  wire   [0:7] Result_add;
  wire   [0:7] Result_mul;

  INV_X0P7M_A9TH U27 ( .A(n42), .Y(n40) );
  NAND2_X1M_A9TH U28 ( .A(operation[0]), .B(operation[1]), .Y(n42) );
  AOI22_X0P5M_A9TH U29 ( .A0(n35), .A1(Result_sub2[4]), .B0(n40), .B1(
        Result_mul[4]), .Y(n39) );
  AOI22_X0P5M_A9TH U30 ( .A0(n35), .A1(Result_sub2[5]), .B0(n40), .B1(
        Result_mul[5]), .Y(n34) );
  AOI22_X0P5M_A9TH U31 ( .A0(n37), .A1(Result_sub1[4]), .B0(n36), .B1(
        Result_add[4]), .Y(n38) );
  AOI22_X0P5M_A9TH U32 ( .A0(n35), .A1(Result_sub2[6]), .B0(n40), .B1(
        Result_mul[6]), .Y(n32) );
  AOI22_X0P5M_A9TH U33 ( .A0(n37), .A1(Result_sub1[5]), .B0(n36), .B1(
        Result_add[5]), .Y(n33) );
  AOI22_X0P5M_A9TH U34 ( .A0(n37), .A1(Result_sub1[6]), .B0(n36), .B1(
        Result_add[6]), .Y(n31) );
  AOI22_X0P5M_A9TH U35 ( .A0(n37), .A1(Result_sub1[7]), .B0(n36), .B1(
        Result_add[7]), .Y(n29) );
  AOI22_X0P5M_A9TH U36 ( .A0(n35), .A1(Result_sub2[7]), .B0(n40), .B1(
        Result_mul[7]), .Y(n30) );
  INV_X0P6M_A9TH U37 ( .A(operation[1]), .Y(n28) );
  INV_X0P6M_A9TH U38 ( .A(operation[0]), .Y(n27) );
  NOR2_X1A_A9TH U39 ( .A(n27), .B(operation[1]), .Y(n35) );
  NOR2_X1A_A9TH U40 ( .A(n28), .B(operation[0]), .Y(n37) );
  AOI22_X1M_A9TH U41 ( .A0(Result_sub2[0]), .A1(n35), .B0(n37), .B1(
        Result_sub1[0]), .Y(n41) );
  OAI2XB1_X0P5M_A9TH U42 ( .A1N(Result_mul[2]), .A0(n42), .B0(n41), .Y(
        Result[2]) );
  OAI2XB1_X0P5M_A9TH U43 ( .A1N(Result_mul[0]), .A0(n42), .B0(n41), .Y(
        Result[0]) );
  NOR2_X1A_A9TH U44 ( .A(operation[1]), .B(operation[0]), .Y(n36) );
  NAND2_X0P5M_A9TH U45 ( .A(n30), .B(n29), .Y(Result[7]) );
  NAND2_X0P5M_A9TH U46 ( .A(n32), .B(n31), .Y(Result[6]) );
  NAND2_X0P5M_A9TH U47 ( .A(n34), .B(n33), .Y(Result[5]) );
  NAND2_X0P5M_A9TH U48 ( .A(n39), .B(n38), .Y(Result[4]) );
  AO21B_X0P5M_A9TH U49 ( .A0(Result_mul[3]), .A1(n40), .B0N(n41), .Y(Result[3]) );
  OAI2XB1_X0P5M_A9TH U50 ( .A1N(Result_mul[1]), .A0(n42), .B0(n41), .Y(
        Result[1]) );
  INV_X0P5B_A9TH \subtractor_1/U7  ( .A(a[3]), .Y(\subtractor_1/n1 ) );
  INV_X0P6M_A9TH \subtractor_1/U6  ( .A(b[2]), .Y(\subtractor_1/intadd_0/B[0] ) );
  NAND2_X0P7M_A9TH \subtractor_1/U5  ( .A(b[3]), .B(\subtractor_1/n1 ), .Y(
        \subtractor_1/intadd_0/CI ) );
  OAI21_X0P5M_A9TH \subtractor_1/U4  ( .A0(b[3]), .A1(\subtractor_1/n1 ), .B0(
        \subtractor_1/intadd_0/CI ), .Y(Result_sub1[7]) );
  INV_X0P8M_A9TH \subtractor_1/U3  ( .A(b[0]), .Y(\subtractor_1/intadd_0/B[2] ) );
  INV_X0P8M_A9TH \subtractor_1/U2  ( .A(\subtractor_1/intadd_0/n1 ), .Y(
        Result_sub1[0]) );
  INV_X0P8M_A9TH \subtractor_1/U1  ( .A(b[1]), .Y(\subtractor_1/intadd_0/B[1] ) );
  ADDF_X1M_A9TH \subtractor_1/intadd_0/U2  ( .A(\subtractor_1/intadd_0/B[2] ), 
        .B(a[0]), .CI(\subtractor_1/intadd_0/n2 ), .CO(
        \subtractor_1/intadd_0/n1 ), .S(Result_sub1[4]) );
  ADDF_X1M_A9TH \subtractor_1/intadd_0/U3  ( .A(\subtractor_1/intadd_0/B[1] ), 
        .B(a[1]), .CI(\subtractor_1/intadd_0/n3 ), .CO(
        \subtractor_1/intadd_0/n2 ), .S(Result_sub1[5]) );
  ADDF_X1M_A9TH \subtractor_1/intadd_0/U4  ( .A(\subtractor_1/intadd_0/B[0] ), 
        .B(a[2]), .CI(\subtractor_1/intadd_0/CI ), .CO(
        \subtractor_1/intadd_0/n3 ), .S(Result_sub1[6]) );
  INV_X0P5B_A9TH \subtractor_2/U7  ( .A(b[3]), .Y(\subtractor_2/n1 ) );
  INV_X0P6M_A9TH \subtractor_2/U6  ( .A(a[2]), .Y(\subtractor_2/intadd_1/B[0] ) );
  NAND2_X0P7M_A9TH \subtractor_2/U5  ( .A(a[3]), .B(\subtractor_2/n1 ), .Y(
        \subtractor_2/intadd_1/CI ) );
  OAI21_X0P5M_A9TH \subtractor_2/U4  ( .A0(a[3]), .A1(\subtractor_2/n1 ), .B0(
        \subtractor_2/intadd_1/CI ), .Y(Result_sub2[7]) );
  INV_X0P8M_A9TH \subtractor_2/U3  ( .A(a[0]), .Y(\subtractor_2/intadd_1/B[2] ) );
  INV_X0P8M_A9TH \subtractor_2/U2  ( .A(a[1]), .Y(\subtractor_2/intadd_1/B[1] ) );
  INV_X0P8M_A9TH \subtractor_2/U1  ( .A(\subtractor_2/intadd_1/n1 ), .Y(
        Result_sub2[0]) );
  ADDF_X1M_A9TH \subtractor_2/intadd_1/U2  ( .A(\subtractor_2/intadd_1/B[2] ), 
        .B(b[0]), .CI(\subtractor_2/intadd_1/n2 ), .CO(
        \subtractor_2/intadd_1/n1 ), .S(Result_sub2[4]) );
  ADDF_X1M_A9TH \subtractor_2/intadd_1/U3  ( .A(\subtractor_2/intadd_1/B[1] ), 
        .B(b[1]), .CI(\subtractor_2/intadd_1/n3 ), .CO(
        \subtractor_2/intadd_1/n2 ), .S(Result_sub2[5]) );
  ADDF_X1M_A9TH \subtractor_2/intadd_1/U4  ( .A(\subtractor_2/intadd_1/B[0] ), 
        .B(b[2]), .CI(\subtractor_2/intadd_1/CI ), .CO(
        \subtractor_2/intadd_1/n3 ), .S(Result_sub2[6]) );
  ADDF_X1M_A9TH \adder_1/U7  ( .A(b[1]), .B(a[1]), .CI(\adder_1/n4 ), .CO(
        \adder_1/n1 ), .S(Result_add[5]) );
  ADDF_X1M_A9TH \adder_1/U6  ( .A(b[2]), .B(a[2]), .CI(\adder_1/n3 ), .CO(
        \adder_1/n4 ), .S(Result_add[6]) );
  XOR3_X0P5M_A9TH \adder_1/U5  ( .A(\adder_1/n1 ), .B(b[0]), .C(a[0]), .Y(
        Result_add[4]) );
  NOR2_X0P5M_A9TH \adder_1/U4  ( .A(a[3]), .B(b[3]), .Y(\adder_1/n2 ) );
  AND2_X0P5M_A9TH \adder_1/U3  ( .A(a[3]), .B(b[3]), .Y(\adder_1/n3 ) );
  NOR2_X0P5M_A9TH \adder_1/U2  ( .A(\adder_1/n2 ), .B(\adder_1/n3 ), .Y(
        Result_add[7]) );
  OAI21_X1M_A9TH \multiplier_1/U69  ( .A0(\multiplier_1/n53 ), .A1(
        \multiplier_1/n50 ), .B0(\multiplier_1/n51 ), .Y(\multiplier_1/n49 )
         );
  OR2_X0P5M_A9TH \multiplier_1/U68  ( .A(\multiplier_1/n39 ), .B(
        \multiplier_1/n38 ), .Y(\multiplier_1/n40 ) );
  ADDF_X1M_A9TH \multiplier_1/U67  ( .A(\multiplier_1/n35 ), .B(
        \multiplier_1/n34 ), .CI(\multiplier_1/n33 ), .CO(\multiplier_1/n36 ), 
        .S(\multiplier_1/n27 ) );
  INV_X0P5B_A9TH \multiplier_1/U66  ( .A(\multiplier_1/n32 ), .Y(
        \multiplier_1/n42 ) );
  AOI21_X1M_A9TH \multiplier_1/U65  ( .A0(\multiplier_1/n29 ), .A1(
        \multiplier_1/n44 ), .B0(\multiplier_1/n28 ), .Y(\multiplier_1/n43 )
         );
  OAI21_X1M_A9TH \multiplier_1/U64  ( .A0(\multiplier_1/n55 ), .A1(
        \multiplier_1/n58 ), .B0(\multiplier_1/n56 ), .Y(\multiplier_1/n44 )
         );
  ADDH_X1M_A9TH \multiplier_1/U63  ( .A(\multiplier_1/n16 ), .B(
        \multiplier_1/n15 ), .CO(\multiplier_1/n10 ), .S(\multiplier_1/n21 )
         );
  NOR2_X1A_A9TH \multiplier_1/U62  ( .A(\multiplier_1/n23 ), .B(
        \multiplier_1/n22 ), .Y(\multiplier_1/n55 ) );
  ADDH_X1M_A9TH \multiplier_1/U61  ( .A(\multiplier_1/n14 ), .B(
        \multiplier_1/n13 ), .CO(\multiplier_1/n7 ), .S(\multiplier_1/n22 ) );
  ADDF_X1M_A9TH \multiplier_1/U60  ( .A(\multiplier_1/n12 ), .B(
        \multiplier_1/n11 ), .CI(\multiplier_1/n10 ), .CO(\multiplier_1/n24 ), 
        .S(\multiplier_1/n23 ) );
  NOR2_X1A_A9TH \multiplier_1/U59  ( .A(\multiplier_1/n27 ), .B(
        \multiplier_1/n26 ), .Y(\multiplier_1/n45 ) );
  ADDH_X1M_A9TH \multiplier_1/U58  ( .A(\multiplier_1/n4 ), .B(
        \multiplier_1/n3 ), .CO(\multiplier_1/n33 ), .S(\multiplier_1/n5 ) );
  NOR2_X1A_A9TH \multiplier_1/U57  ( .A(\multiplier_1/n2 ), .B(
        \multiplier_1/n30 ), .Y(\multiplier_1/n34 ) );
  NOR2_X1A_A9TH \multiplier_1/U56  ( .A(\multiplier_1/n31 ), .B(
        \multiplier_1/n17 ), .Y(\multiplier_1/n35 ) );
  NOR2_X1A_A9TH \multiplier_1/U55  ( .A(\multiplier_1/n25 ), .B(
        \multiplier_1/n24 ), .Y(\multiplier_1/n50 ) );
  NOR2_X1A_A9TH \multiplier_1/U54  ( .A(\multiplier_1/n18 ), .B(
        \multiplier_1/n19 ), .Y(\multiplier_1/n16 ) );
  NOR2_X1A_A9TH \multiplier_1/U53  ( .A(\multiplier_1/n2 ), .B(
        \multiplier_1/n19 ), .Y(\multiplier_1/n11 ) );
  NOR2_X1A_A9TH \multiplier_1/U52  ( .A(\multiplier_1/n31 ), .B(
        \multiplier_1/n65 ), .Y(\multiplier_1/n12 ) );
  NOR2_X1A_A9TH \multiplier_1/U51  ( .A(\multiplier_1/n31 ), .B(
        \multiplier_1/n19 ), .Y(\multiplier_1/n3 ) );
  NOR2_X1A_A9TH \multiplier_1/U50  ( .A(\multiplier_1/n18 ), .B(
        \multiplier_1/n30 ), .Y(\multiplier_1/n4 ) );
  NOR2_X1A_A9TH \multiplier_1/U49  ( .A(\multiplier_1/n18 ), .B(
        \multiplier_1/n17 ), .Y(\multiplier_1/n13 ) );
  INV_X0P8M_A9TH \multiplier_1/U48  ( .A(a[0]), .Y(\multiplier_1/n30 ) );
  INV_X0P5B_A9TH \multiplier_1/U47  ( .A(\multiplier_1/n44 ), .Y(
        \multiplier_1/n53 ) );
  INV_X0P5B_A9TH \multiplier_1/U46  ( .A(\multiplier_1/n60 ), .Y(
        \multiplier_1/n62 ) );
  INV_X0P5B_A9TH \multiplier_1/U45  ( .A(\multiplier_1/n50 ), .Y(
        \multiplier_1/n52 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U44  ( .A(\multiplier_1/n54 ), .B(
        \multiplier_1/n53 ), .Y(Result_mul[3]) );
  XOR2_X0P5M_A9TH \multiplier_1/U43  ( .A(\multiplier_1/n64 ), .B(
        \multiplier_1/n63 ), .Y(Result_mul[5]) );
  INV_X0P5B_A9TH \multiplier_1/U42  ( .A(\multiplier_1/n55 ), .Y(
        \multiplier_1/n57 ) );
  XOR2_X0P5M_A9TH \multiplier_1/U41  ( .A(\multiplier_1/n59 ), .B(
        \multiplier_1/n58 ), .Y(Result_mul[4]) );
  INV_X0P5B_A9TH \multiplier_1/U40  ( .A(\multiplier_1/n45 ), .Y(
        \multiplier_1/n47 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U39  ( .A(\multiplier_1/n25 ), .B(
        \multiplier_1/n24 ), .Y(\multiplier_1/n51 ) );
  INV_X0P8M_A9TH \multiplier_1/U38  ( .A(a[2]), .Y(\multiplier_1/n19 ) );
  INV_X0P6M_A9TH \multiplier_1/U37  ( .A(b[3]), .Y(\multiplier_1/n66 ) );
  INV_X0P7M_A9TH \multiplier_1/U36  ( .A(b[0]), .Y(\multiplier_1/n31 ) );
  NOR2_X1A_A9TH \multiplier_1/U35  ( .A(\multiplier_1/n2 ), .B(
        \multiplier_1/n65 ), .Y(\multiplier_1/n15 ) );
  XNOR2_X0P5M_A9TH \multiplier_1/U34  ( .A(\multiplier_1/n7 ), .B(
        \multiplier_1/n6 ), .Y(\multiplier_1/n1 ) );
  INV_X0P6M_A9TH \multiplier_1/U33  ( .A(\multiplier_1/n36 ), .Y(
        \multiplier_1/n41 ) );
  XNOR2_X0P5M_A9TH \multiplier_1/U32  ( .A(\multiplier_1/n1 ), .B(
        \multiplier_1/n5 ), .Y(\multiplier_1/n25 ) );
  OAI21_X0P7M_A9TH \multiplier_1/U31  ( .A0(\multiplier_1/n51 ), .A1(
        \multiplier_1/n45 ), .B0(\multiplier_1/n46 ), .Y(\multiplier_1/n28 )
         );
  OAI21_X0P7M_A9TH \multiplier_1/U30  ( .A0(\multiplier_1/n43 ), .A1(
        \multiplier_1/n42 ), .B0(\multiplier_1/n41 ), .Y(Result_mul[0]) );
  XOR2_X0P5M_A9TH \multiplier_1/U29  ( .A(\multiplier_1/n43 ), .B(
        \multiplier_1/n37 ), .Y(Result_mul[1]) );
  XNOR2_X0P5M_A9TH \multiplier_1/U28  ( .A(\multiplier_1/n49 ), .B(
        \multiplier_1/n48 ), .Y(Result_mul[2]) );
  INV_X0P7M_A9TH \multiplier_1/U27  ( .A(a[1]), .Y(\multiplier_1/n17 ) );
  INV_X0P7M_A9TH \multiplier_1/U26  ( .A(b[2]), .Y(\multiplier_1/n18 ) );
  INV_X0P7M_A9TH \multiplier_1/U25  ( .A(b[1]), .Y(\multiplier_1/n2 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U24  ( .A(\multiplier_1/n66 ), .B(
        \multiplier_1/n17 ), .Y(\multiplier_1/n20 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U23  ( .A(\multiplier_1/n66 ), .B(
        \multiplier_1/n19 ), .Y(\multiplier_1/n38 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U22  ( .A(\multiplier_1/n18 ), .B(
        \multiplier_1/n65 ), .Y(\multiplier_1/n39 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U21  ( .A(\multiplier_1/n2 ), .B(
        \multiplier_1/n17 ), .Y(\multiplier_1/n6 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U20  ( .A(\multiplier_1/n66 ), .B(
        \multiplier_1/n65 ), .Y(Result_mul[7]) );
  NOR2_X0P5M_A9TH \multiplier_1/U19  ( .A(\multiplier_1/n31 ), .B(
        \multiplier_1/n30 ), .Y(\multiplier_1/n32 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U18  ( .A(\multiplier_1/n39 ), .B(
        \multiplier_1/n38 ), .Y(\multiplier_1/n63 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U17  ( .A(\multiplier_1/n7 ), .B(
        \multiplier_1/n6 ), .Y(\multiplier_1/n8 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U16  ( .A(\multiplier_1/n21 ), .B(
        \multiplier_1/n20 ), .Y(\multiplier_1/n60 ) );
  AND2_X0P5M_A9TH \multiplier_1/U15  ( .A(\multiplier_1/n40 ), .B(
        \multiplier_1/n63 ), .Y(Result_mul[6]) );
  OAI21_X0P5M_A9TH \multiplier_1/U14  ( .A0(\multiplier_1/n7 ), .A1(
        \multiplier_1/n6 ), .B0(\multiplier_1/n5 ), .Y(\multiplier_1/n9 ) );
  NAND2_X0P7M_A9TH \multiplier_1/U13  ( .A(\multiplier_1/n23 ), .B(
        \multiplier_1/n22 ), .Y(\multiplier_1/n56 ) );
  OA21_X0P5M_A9TH \multiplier_1/U12  ( .A0(\multiplier_1/n60 ), .A1(
        \multiplier_1/n63 ), .B0(\multiplier_1/n61 ), .Y(\multiplier_1/n58 )
         );
  NAND2_X0P5M_A9TH \multiplier_1/U11  ( .A(\multiplier_1/n9 ), .B(
        \multiplier_1/n8 ), .Y(\multiplier_1/n26 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U10  ( .A(\multiplier_1/n62 ), .B(
        \multiplier_1/n61 ), .Y(\multiplier_1/n64 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U9  ( .A(\multiplier_1/n50 ), .B(
        \multiplier_1/n45 ), .Y(\multiplier_1/n29 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U8  ( .A(\multiplier_1/n57 ), .B(
        \multiplier_1/n56 ), .Y(\multiplier_1/n59 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U7  ( .A(\multiplier_1/n52 ), .B(
        \multiplier_1/n51 ), .Y(\multiplier_1/n54 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U6  ( .A(\multiplier_1/n47 ), .B(
        \multiplier_1/n46 ), .Y(\multiplier_1/n48 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U5  ( .A(\multiplier_1/n21 ), .B(
        \multiplier_1/n20 ), .Y(\multiplier_1/n61 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U4  ( .A(\multiplier_1/n27 ), .B(
        \multiplier_1/n26 ), .Y(\multiplier_1/n46 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U3  ( .A(\multiplier_1/n32 ), .B(
        \multiplier_1/n41 ), .Y(\multiplier_1/n37 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U2  ( .A(\multiplier_1/n66 ), .B(
        \multiplier_1/n30 ), .Y(\multiplier_1/n14 ) );
  INV_X1M_A9TH \multiplier_1/U1  ( .A(a[3]), .Y(\multiplier_1/n65 ) );
endmodule

