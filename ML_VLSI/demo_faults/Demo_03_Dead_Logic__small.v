// Presentation demo: U2/U3 form logic that never contributes to the output y.
module demo_dead_logic (a, b, y);
  input a, b;
  output y;
  wire unused_n1, unused_n2;

  NAND2_X1M_A9TH U1 (.A(a), .B(b), .Y(y));
  NAND2_X1M_A9TH U2 (.A(a), .B(b), .Y(unused_n1));
  INV_X1M_A9TH   U3 (.A(unused_n1), .Y(unused_n2));
endmodule
