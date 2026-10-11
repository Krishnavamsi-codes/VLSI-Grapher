/////////////////////////////////////////////////////////////
// Created by: Synopsys DC Ultra(TM) in wire load mode
// Version   : O-2018.06-SP5-5
// Date      : Thu Sep 24 21:15:50 2020
/////////////////////////////////////////////////////////////


module add_mul_mix_2_bit ( a, b, c, d, Result );
  input [0:1] a;
  input [0:1] b;
  input [0:1] c;
  input [0:1] d;
  output [0:3] Result;
  wire   \adder_1/n1 , \adder_2/n1 , \multiplier_1/n2 , \multiplier_1/n1 ;
  wire   [0:1] Result_add;
  wire   [0:1] Result_add_2;

  OA21_X1M_A9TH \adder_1/U3  ( .A0(a[1]), .A1(b[1]), .B0(\adder_1/n1 ), .Y(
        Result_add[1]) );
  XNOR3_X0P5M_A9TH \adder_1/U2  ( .A(b[0]), .B(a[0]), .C(\adder_1/n1 ), .Y(
        Result_add[0]) );
  NAND2_X1M_A9TH \adder_1/U1  ( .A(a[1]), .B(b[1]), .Y(\adder_1/n1 ) );
  OA21_X1M_A9TH \adder_2/U3  ( .A0(c[1]), .A1(d[1]), .B0(\adder_2/n1 ), .Y(
        Result_add_2[1]) );
  XNOR3_X0P5M_A9TH \adder_2/U2  ( .A(d[0]), .B(c[0]), .C(\adder_2/n1 ), .Y(
        Result_add_2[0]) );
  NAND2_X1M_A9TH \adder_2/U1  ( .A(c[1]), .B(d[1]), .Y(\adder_2/n1 ) );
  NOR2_X0P5M_A9TH \multiplier_1/U6  ( .A(Result[0]), .B(\multiplier_1/n2 ), 
        .Y(Result[2]) );
  NOR2_X0P5M_A9TH \multiplier_1/U5  ( .A(Result[3]), .B(\multiplier_1/n1 ), 
        .Y(Result[1]) );
  AND2_X1M_A9TH \multiplier_1/U4  ( .A(Result_add[1]), .B(Result_add_2[1]), 
        .Y(Result[3]) );
  AOI22_X0P7M_A9TH \multiplier_1/U3  ( .A0(Result_add[0]), .A1(Result_add_2[1]), .B0(Result_add_2[0]), .B1(Result_add[1]), .Y(\multiplier_1/n2 ) );
  NAND2_X0P7A_A9TH \multiplier_1/U2  ( .A(Result_add[0]), .B(Result_add_2[0]), 
        .Y(\multiplier_1/n1 ) );
  AND3_X0P7M_A9TH \multiplier_1/U1  ( .A(Result_add[0]), .B(Result_add_2[0]), 
        .C(Result[3]), .Y(Result[0]) );
endmodule

