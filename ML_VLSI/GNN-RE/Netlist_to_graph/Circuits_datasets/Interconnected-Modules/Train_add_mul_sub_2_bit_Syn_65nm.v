/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : O-2018.06-SP5-5
// Date      : Sun Sep 27 00:04:03 2020
/////////////////////////////////////////////////////////////


module add_mul_sub_2_bit ( a, b, operation, Result );
  input [0:1] a;
  input [0:1] b;
  input [0:1] operation;
  output [0:3] Result;
  wire   n16, n17, n18, n19, n20, n21, n22, n23, n24, n25, \subtractor_1/n4 ,
         \subtractor_1/n3 , \subtractor_1/n2 , \subtractor_1/n1 ,
         \subtractor_2/n4 , \subtractor_2/n3 , \subtractor_2/n2 ,
         \subtractor_2/n1 , \adder_1/n1 , \multiplier_1/n2 , \multiplier_1/n1 
;
  wire   [0:3] Result_sub1;
  wire   [0:3] Result_sub2;
  wire   [0:3] Result_add;
  wire   [0:3] Result_mul;

  OAI221_X0P5M_A9TH U16 ( .A0(operation[0]), .A1(Result_add[3]), .B0(n23), 
        .B1(Result_sub2[3]), .C0(n22), .Y(n16) );
  AOI22_X0P5M_A9TH U17 ( .A0(n21), .A1(Result_sub1[2]), .B0(n20), .B1(
        Result_mul[2]), .Y(n25) );
  AOI22_X0P5M_A9TH U18 ( .A0(n21), .A1(Result_sub1[3]), .B0(n20), .B1(
        Result_mul[3]), .Y(n17) );
  NOR2_X0P5M_A9TH U19 ( .A(operation[1]), .B(n23), .Y(n18) );
  INV_X0P7M_A9TH U20 ( .A(operation[0]), .Y(n23) );
  INV_X0P7M_A9TH U21 ( .A(operation[1]), .Y(n22) );
  AOI22_X0P7M_A9TH U22 ( .A0(n18), .A1(Result_sub2[0]), .B0(n21), .B1(
        Result_sub1[0]), .Y(n19) );
  OAI221_X0P7M_A9TH U23 ( .A0(operation[0]), .A1(Result_add[2]), .B0(n23), 
        .B1(Result_sub2[2]), .C0(n22), .Y(n24) );
  NOR2_X1A_A9TH U24 ( .A(operation[0]), .B(n22), .Y(n21) );
  NOR2_X1A_A9TH U25 ( .A(n22), .B(n23), .Y(n20) );
  NAND2_X0P5M_A9TH U26 ( .A(n17), .B(n16), .Y(Result[3]) );
  AO21B_X0P5M_A9TH U27 ( .A0(Result_mul[1]), .A1(n20), .B0N(n19), .Y(Result[1]) );
  AO21B_X0P5M_A9TH U28 ( .A0(Result_mul[0]), .A1(n20), .B0N(n19), .Y(Result[0]) );
  NAND2_X0P5M_A9TH U29 ( .A(n25), .B(n24), .Y(Result[2]) );
  ADDF_X1M_A9TH \subtractor_1/U6  ( .A(\subtractor_1/n4 ), .B(a[0]), .CI(
        \subtractor_1/n3 ), .CO(\subtractor_1/n1 ), .S(Result_sub1[2]) );
  INV_X0P5B_A9TH \subtractor_1/U5  ( .A(\subtractor_1/n1 ), .Y(Result_sub1[0])
         );
  INV_X0P5B_A9TH \subtractor_1/U4  ( .A(a[1]), .Y(\subtractor_1/n2 ) );
  NAND2_X0P7M_A9TH \subtractor_1/U3  ( .A(b[1]), .B(\subtractor_1/n2 ), .Y(
        \subtractor_1/n3 ) );
  INV_X0P6M_A9TH \subtractor_1/U2  ( .A(b[0]), .Y(\subtractor_1/n4 ) );
  OAI21_X0P5M_A9TH \subtractor_1/U1  ( .A0(b[1]), .A1(\subtractor_1/n2 ), .B0(
        \subtractor_1/n3 ), .Y(Result_sub1[3]) );
  ADDF_X1M_A9TH \subtractor_2/U6  ( .A(\subtractor_2/n4 ), .B(b[0]), .CI(
        \subtractor_2/n3 ), .CO(\subtractor_2/n1 ), .S(Result_sub2[2]) );
  INV_X0P5B_A9TH \subtractor_2/U5  ( .A(b[1]), .Y(\subtractor_2/n2 ) );
  INV_X0P5B_A9TH \subtractor_2/U4  ( .A(\subtractor_2/n1 ), .Y(Result_sub2[0])
         );
  NAND2_X0P7M_A9TH \subtractor_2/U3  ( .A(a[1]), .B(\subtractor_2/n2 ), .Y(
        \subtractor_2/n3 ) );
  INV_X0P6M_A9TH \subtractor_2/U2  ( .A(a[0]), .Y(\subtractor_2/n4 ) );
  OAI21_X0P5M_A9TH \subtractor_2/U1  ( .A0(a[1]), .A1(\subtractor_2/n2 ), .B0(
        \subtractor_2/n3 ), .Y(Result_sub2[3]) );
  XNOR3_X0P5M_A9TH \adder_1/U4  ( .A(b[0]), .B(a[0]), .C(\adder_1/n1 ), .Y(
        Result_add[2]) );
  NAND2_X0P5M_A9TH \adder_1/U3  ( .A(a[1]), .B(b[1]), .Y(\adder_1/n1 ) );
  OA21_X0P5M_A9TH \adder_1/U2  ( .A0(a[1]), .A1(b[1]), .B0(\adder_1/n1 ), .Y(
        Result_add[3]) );
  AND2_X0P5M_A9TH \multiplier_1/U6  ( .A(a[1]), .B(b[1]), .Y(Result_mul[3]) );
  NAND2_X0P5M_A9TH \multiplier_1/U5  ( .A(a[0]), .B(b[0]), .Y(
        \multiplier_1/n1 ) );
  AOI22_X0P5M_A9TH \multiplier_1/U4  ( .A0(a[0]), .A1(b[1]), .B0(b[0]), .B1(
        a[1]), .Y(\multiplier_1/n2 ) );
  AND3_X0P5M_A9TH \multiplier_1/U3  ( .A(a[0]), .B(b[0]), .C(Result_mul[3]), 
        .Y(Result_mul[0]) );
  NOR2_X0P5M_A9TH \multiplier_1/U2  ( .A(Result_mul[3]), .B(\multiplier_1/n1 ), 
        .Y(Result_mul[1]) );
  NOR2_X0P5M_A9TH \multiplier_1/U1  ( .A(Result_mul[0]), .B(\multiplier_1/n2 ), 
        .Y(Result_mul[2]) );
endmodule

