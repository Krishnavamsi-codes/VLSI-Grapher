// Broken 2-bit ripple-carry adder for demonstration.
// Error: sum[1] is declared as an output but no gate drives it. U2 sends its sum to unused_sum1 instead.
module two_bit_adder_wrong_undriven_output (a, b, cin, sum, cout);
  input [1:0] a, b;
  input cin;
  output [1:0] sum;
  output cout;
  wire carry0, unused_sum1;

  ADDF_X1M_A9TH U1 (.A(a[0]), .B(b[0]), .CI(cin),    .S(sum[0]),      .CO(carry0));
  ADDF_X1M_A9TH U2 (.A(a[1]), .B(b[1]), .CI(carry0), .S(unused_sum1), .CO(cout));
endmodule
