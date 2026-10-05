// Correct 1-bit half subtractor: difference = a XOR b; borrow = (NOT a) AND b.
module half_subtractor_correct (a, b, difference, borrow);
  input a, b;
  output difference, borrow;
  wire not_a;

  XOR2_X1M_A9TH U1 (.A(a), .B(b), .Y(difference));
  INV_X1M_A9TH  U2 (.A(a), .Y(not_a));
  AND2_X1M_A9TH U3 (.A(not_a), .B(b), .Y(borrow));
endmodule
