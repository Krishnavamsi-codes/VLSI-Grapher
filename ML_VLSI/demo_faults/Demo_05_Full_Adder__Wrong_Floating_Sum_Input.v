// Broken 1-bit full adder for demonstration.
// Error: U2 should use cin, but it reads missing_cin instead. Sum is therefore not reliable.
module full_adder_wrong_floating_sum_input (a, b, cin, sum, cout);
  input a, b, cin;
  output sum, cout;
  wire a_xor_b, carry_ab, carry_cin, missing_cin;

  XOR2_X1M_A9TH U1 (.A(a),       .B(b),           .Y(a_xor_b));
  XOR2_X1M_A9TH U2 (.A(a_xor_b), .B(missing_cin), .Y(sum));
  AND2_X1M_A9TH U3 (.A(a),       .B(b),           .Y(carry_ab));
  AND2_X1M_A9TH U4 (.A(a_xor_b), .B(cin),         .Y(carry_cin));
  OR2_X1M_A9TH  U5 (.A(carry_ab), .B(carry_cin), .Y(cout));
endmodule
