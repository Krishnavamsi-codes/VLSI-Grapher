// Broken half subtractor for demonstration.
// Error: pin B of U1 is left blank (.B()). The XOR has a missing input, so difference is unreliable.
module half_subtractor_wrong_missing_pin (a, b, difference, borrow);
  input a, b;
  output difference, borrow;
  wire not_a;

  XOR2_X1M_A9TH U1 (.A(a), .B(), .Y(difference));
  INV_X1M_A9TH  U2 (.A(a), .Y(not_a));
  AND2_X1M_A9TH U3 (.A(not_a), .B(b), .Y(borrow));
endmodule
