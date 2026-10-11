/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : O-2018.06-SP5-5
// Date      : Mon Sep 28 12:47:28 2020
/////////////////////////////////////////////////////////////


module add_mul_comp_sub_2_bit ( a, b, Result );
  input [0:1] a;
  input [0:1] b;
  output [0:3] Result;
  wire   n16, n17, n18, n19, n20, n21, n22, n23, n24, n25, n26,
         \subtractor_1/n6 , \subtractor_1/n5 , \subtractor_1/n4 ,
         \subtractor_1/n3 , \subtractor_1/n1 , \comparator_1/n5 ,
         \comparator_1/n4 , \comparator_1/n3 , \comparator_1/n2 ,
         \comparator_1/n1 , \subtractor_2/n4 , \subtractor_2/n3 ,
         \subtractor_2/n2 , \subtractor_2/n1 , \adder_1/n1 , \multiplier_1/n2 ,
         \multiplier_1/n1 ;
  wire   [0:3] Result_sub1;
  wire   [0:1] operation;
  wire   [0:3] Result_sub2;
  wire   [0:3] Result_add;
  wire   [0:3] Result_mul;

  INV_X0P8M_A9TH U16 ( .A(operation[1]), .Y(n24) );
  INV_X0P8M_A9TH U17 ( .A(operation[0]), .Y(n23) );
  AOI21_X1M_A9TH U18 ( .A0(n22), .A1(Result_sub2[0]), .B0(n19), .Y(n20) );
  AOI22_X0P5M_A9TH U19 ( .A0(n22), .A1(Result_sub2[3]), .B0(n21), .B1(
        Result_mul[3]), .Y(n17) );
  AOI22_X0P5M_A9TH U20 ( .A0(n22), .A1(Result_sub2[2]), .B0(n21), .B1(
        Result_mul[2]), .Y(n26) );
  NAND2_X0P5M_A9TH U21 ( .A(operation[1]), .B(n23), .Y(n18) );
  NOR2_X1A_A9TH U22 ( .A(n23), .B(n24), .Y(n21) );
  OAI221_X0P5M_A9TH U23 ( .A0(operation[1]), .A1(Result_add[3]), .B0(n24), 
        .B1(Result_sub1[3]), .C0(n23), .Y(n16) );
  AO21B_X0P5M_A9TH U24 ( .A0(Result_mul[0]), .A1(n21), .B0N(n20), .Y(Result[0]) );
  AO21B_X0P5M_A9TH U25 ( .A0(Result_mul[1]), .A1(n21), .B0N(n20), .Y(Result[1]) );
  NOR2_X0P7A_A9TH U26 ( .A(Result_sub1[0]), .B(n18), .Y(n19) );
  OAI221_X0P7M_A9TH U27 ( .A0(operation[1]), .A1(Result_add[2]), .B0(n24), 
        .B1(Result_sub1[2]), .C0(n23), .Y(n25) );
  NOR2_X0P7A_A9TH U28 ( .A(operation[1]), .B(n23), .Y(n22) );
  NAND2_X0P5M_A9TH U29 ( .A(n17), .B(n16), .Y(Result[3]) );
  NAND2_X0P5M_A9TH U30 ( .A(n26), .B(n25), .Y(Result[2]) );
  ADDF_X1M_A9TH \subtractor_1/U7  ( .A(b[0]), .B(\subtractor_1/n3 ), .CI(
        \subtractor_1/n5 ), .CO(\subtractor_1/n1 ), .S(\subtractor_1/n4 ) );
  INV_X0P5B_A9TH \subtractor_1/U6  ( .A(\subtractor_1/n1 ), .Y(Result_sub1[0])
         );
  INV_X0P5B_A9TH \subtractor_1/U5  ( .A(\subtractor_1/n4 ), .Y(Result_sub1[2])
         );
  INV_X0P5B_A9TH \subtractor_1/U4  ( .A(b[1]), .Y(\subtractor_1/n6 ) );
  NOR2_X0P7A_A9TH \subtractor_1/U3  ( .A(a[1]), .B(\subtractor_1/n6 ), .Y(
        \subtractor_1/n5 ) );
  AO21_X0P5M_A9TH \subtractor_1/U2  ( .A0(a[1]), .A1(\subtractor_1/n6 ), .B0(
        \subtractor_1/n5 ), .Y(Result_sub1[3]) );
  INV_X0P6M_A9TH \subtractor_1/U1  ( .A(a[0]), .Y(\subtractor_1/n3 ) );
  AOI221_X1M_A9TH \comparator_1/U7  ( .A0(\comparator_1/n5 ), .A1(b[0]), .B0(
        a[1]), .B1(\comparator_1/n4 ), .C0(\comparator_1/n3 ), .Y(operation[1]) );
  OAI22_X0P7M_A9TH \comparator_1/U6  ( .A0(b[0]), .A1(\comparator_1/n5 ), .B0(
        \comparator_1/n2 ), .B1(\comparator_1/n1 ), .Y(operation[0]) );
  INV_X1M_A9TH \comparator_1/U5  ( .A(a[0]), .Y(\comparator_1/n5 ) );
  INV_X0P6M_A9TH \comparator_1/U4  ( .A(b[1]), .Y(\comparator_1/n4 ) );
  AND2_X0P5M_A9TH \comparator_1/U3  ( .A(\comparator_1/n5 ), .B(b[0]), .Y(
        \comparator_1/n2 ) );
  NAND2_X0P5M_A9TH \comparator_1/U2  ( .A(a[1]), .B(\comparator_1/n4 ), .Y(
        \comparator_1/n1 ) );
  OAI22_X0P5M_A9TH \comparator_1/U1  ( .A0(\comparator_1/n5 ), .A1(b[0]), .B0(
        \comparator_1/n4 ), .B1(a[1]), .Y(\comparator_1/n3 ) );
  ADDF_X1M_A9TH \subtractor_2/U6  ( .A(\subtractor_2/n4 ), .B(b[0]), .CI(
        \subtractor_2/n3 ), .CO(\subtractor_2/n1 ), .S(Result_sub2[2]) );
  INV_X0P5B_A9TH \subtractor_2/U5  ( .A(\subtractor_2/n1 ), .Y(Result_sub2[0])
         );
  INV_X0P5B_A9TH \subtractor_2/U4  ( .A(b[1]), .Y(\subtractor_2/n2 ) );
  INV_X0P5B_A9TH \subtractor_2/U3  ( .A(a[0]), .Y(\subtractor_2/n4 ) );
  NAND2_X0P7M_A9TH \subtractor_2/U2  ( .A(a[1]), .B(\subtractor_2/n2 ), .Y(
        \subtractor_2/n3 ) );
  OAI21_X0P5M_A9TH \subtractor_2/U1  ( .A0(a[1]), .A1(\subtractor_2/n2 ), .B0(
        \subtractor_2/n3 ), .Y(Result_sub2[3]) );
  XNOR3_X0P5M_A9TH \adder_1/U4  ( .A(b[0]), .B(a[0]), .C(\adder_1/n1 ), .Y(
        Result_add[2]) );
  NAND2_X0P5M_A9TH \adder_1/U3  ( .A(a[1]), .B(b[1]), .Y(\adder_1/n1 ) );
  OA21_X0P5M_A9TH \adder_1/U2  ( .A0(a[1]), .A1(b[1]), .B0(\adder_1/n1 ), .Y(
        Result_add[3]) );
  AOI22_X0P5M_A9TH \multiplier_1/U6  ( .A0(a[0]), .A1(b[1]), .B0(b[0]), .B1(
        a[1]), .Y(\multiplier_1/n2 ) );
  NAND2_X0P5M_A9TH \multiplier_1/U5  ( .A(a[0]), .B(b[0]), .Y(
        \multiplier_1/n1 ) );
  AND2_X0P5M_A9TH \multiplier_1/U4  ( .A(a[1]), .B(b[1]), .Y(Result_mul[3]) );
  NOR2_X0P5M_A9TH \multiplier_1/U3  ( .A(Result_mul[3]), .B(\multiplier_1/n1 ), 
        .Y(Result_mul[1]) );
  AND3_X0P5M_A9TH \multiplier_1/U2  ( .A(a[0]), .B(b[0]), .C(Result_mul[3]), 
        .Y(Result_mul[0]) );
  NOR2_X0P5M_A9TH \multiplier_1/U1  ( .A(Result_mul[0]), .B(\multiplier_1/n2 ), 
        .Y(Result_mul[2]) );
endmodule

