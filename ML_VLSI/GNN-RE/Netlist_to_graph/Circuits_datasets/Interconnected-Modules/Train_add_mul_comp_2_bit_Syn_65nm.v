/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : O-2018.06-SP5-5
// Date      : Sat Sep 26 22:59:50 2020
/////////////////////////////////////////////////////////////


module add_mul_comp_2_bit ( a, b, Result );
  input [0:1] a;
  input [0:1] b;
  output [0:3] Result;
  wire   A_greater_B, \adder_1/n1 , \multiplier_1/n2 , \multiplier_1/n1 ,
         \comparator_1/n2 , \comparator_1/n1 ;
  wire   [0:3] Result_add;
  wire   [0:3] Result_mul;

  MX2_X0P5M_A9TH U5 ( .A(Result_add[2]), .B(Result_mul[2]), .S0(A_greater_B), 
        .Y(Result[2]) );
  MX2_X0P5M_A9TH U6 ( .A(Result_add[3]), .B(Result_mul[3]), .S0(A_greater_B), 
        .Y(Result[3]) );
  AND2_X0P5M_A9TH U7 ( .A(A_greater_B), .B(Result_mul[0]), .Y(Result[0]) );
  AND2_X0P5M_A9TH U8 ( .A(A_greater_B), .B(Result_mul[1]), .Y(Result[1]) );
  XNOR3_X0P5M_A9TH \adder_1/U4  ( .A(b[0]), .B(a[0]), .C(\adder_1/n1 ), .Y(
        Result_add[2]) );
  NAND2_X1M_A9TH \adder_1/U3  ( .A(a[1]), .B(b[1]), .Y(\adder_1/n1 ) );
  OA21_X0P7M_A9TH \adder_1/U2  ( .A0(a[1]), .A1(b[1]), .B0(\adder_1/n1 ), .Y(
        Result_add[3]) );
  AND3_X1M_A9TH \multiplier_1/U6  ( .A(a[0]), .B(b[0]), .C(Result_mul[3]), .Y(
        Result_mul[0]) );
  AND2_X1M_A9TH \multiplier_1/U5  ( .A(a[1]), .B(b[1]), .Y(Result_mul[3]) );
  NAND2_X0P7M_A9TH \multiplier_1/U4  ( .A(a[0]), .B(b[0]), .Y(
        \multiplier_1/n1 ) );
  NOR2_X0P7A_A9TH \multiplier_1/U3  ( .A(Result_mul[3]), .B(\multiplier_1/n1 ), 
        .Y(Result_mul[1]) );
  NOR2_X0P7A_A9TH \multiplier_1/U2  ( .A(Result_mul[0]), .B(\multiplier_1/n2 ), 
        .Y(Result_mul[2]) );
  AOI22_X0P5M_A9TH \multiplier_1/U1  ( .A0(a[0]), .A1(b[1]), .B0(b[0]), .B1(
        a[1]), .Y(\multiplier_1/n2 ) );
  OAI22_X1M_A9TH \comparator_1/U3  ( .A0(b[1]), .A1(\comparator_1/n2 ), .B0(
        \comparator_1/n1 ), .B1(b[0]), .Y(A_greater_B) );
  INV_X0P7M_A9TH \comparator_1/U2  ( .A(a[0]), .Y(\comparator_1/n1 ) );
  AO21B_X1M_A9TH \comparator_1/U1  ( .A0(b[0]), .A1(\comparator_1/n1 ), .B0N(
        a[1]), .Y(\comparator_1/n2 ) );
endmodule

