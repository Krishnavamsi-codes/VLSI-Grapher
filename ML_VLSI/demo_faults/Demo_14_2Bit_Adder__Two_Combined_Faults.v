// Broken 2-bit ripple-carry adder for demonstration: two independent mistakes.
// Mistake 1: U2 reads missing_carry instead of the carry0 produced by U1.
// Mistake 2: U2 writes its sum to unused_sum1, leaving primary output sum[1] undriven.
module two_bit_adder_two_combined_faults (a, b, cin, sum, cout);
  input [1:0] a, b;
  input cin;
  output [1:0] sum;
  output cout;
  wire carry0, missing_carry, unused_sum1;

  ADDF_X1M_A9TH U1 (.A(a[0]), .B(b[0]), .CI(cin),           .S(sum[0]),      .CO(carry0));
  ADDF_X1M_A9TH U2 (.A(a[1]), .B(b[1]), .CI(missing_carry), .S(unused_sum1), .CO(cout));
endmodule
